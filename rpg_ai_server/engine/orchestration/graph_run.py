"""Bounded graph execution with lock-ownership keeper."""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from langgraph.errors import GraphRecursionError

from ...config.settings import settings
from ...redis.game_state import GameStateManager
from ...schemas.state import GameState
from ...utils.logger import logger

async def run_graph(
    compiled_graph: Any, state_mgr: GameStateManager,
    state: GameState, uuid: str, worker_id: str,
) -> Dict[str, Any]:
    """Run the graph with a wall-clock timeout and bounded recursion."""
    lock_lost: list[bool] = []

    async def _keep_lock_alive(graph_task: asyncio.Task):
        while True:
            await asyncio.sleep(settings.app.lock_refresh_interval)
            if graph_task.done():
                return
            if not await state_mgr.refresh_lock(uuid, worker_id):
                logger.warning(f"Lost lock ownership for {uuid}, aborting graph run")
                lock_lost.append(True)
                graph_task.cancel()
                return

    graph_task: asyncio.Task = asyncio.create_task(
        compiled_graph.ainvoke(
            state,
            config={"recursion_limit": settings.app.loop_recursion_limit},
        )
    )
    keeper = asyncio.create_task(_keep_lock_alive(graph_task))
    try:
        # shield: wait_for timeout cancels the wait, not graph_task itself;
        # we cancel graph_task explicitly so no orphan run survives lock loss.
        return await asyncio.wait_for(
            asyncio.shield(graph_task),
            timeout=settings.app.request_timeout_seconds,
        )
    except GraphRecursionError as e:
        logger.error(f"Graph recursion limit reached for {uuid}: {e}")
        if not graph_task.done():
            graph_task.cancel()
        raise
    except asyncio.TimeoutError:
        logger.error(f"Graph execution timed out for {uuid} after {settings.app.request_timeout_seconds}s")
        if not graph_task.done():
            graph_task.cancel()
        raise
    except asyncio.CancelledError:
        if lock_lost:
            # Lock stolen mid-run: convert to TimeoutError so process_request
            # returns a graceful story and the ENGINE KEEPS RUNNING.
            # (Raw CancelledError would bubble to MultiTaskEngine.run and
            # kill the whole worker loop.)
            logger.error(f"Graph run aborted (lock lost) for {uuid}")
            raise asyncio.TimeoutError(f"lock lost for {uuid}")
        logger.error(f"Graph run cancelled (shutdown) for {uuid}")
        raise
    finally:
        keeper.cancel()
        try:
            await keeper
        except asyncio.CancelledError:
            pass
