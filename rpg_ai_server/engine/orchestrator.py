from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from langgraph.errors import GraphRecursionError
from langgraph.graph import StateGraph

from ..agents.node4_tool_agent.tools import json_data_maker_and_tracker
from ..config.settings import settings
from ..redis.game_state import GameStateManager
from ..redis.output_cache import OutputCache
from ..schemas.state import GameState
from ..schemas.types import CharacterStats, GameRequest, Skill
from ..scripts.world_generator import generate_world, world_to_grid_data, world_to_meta
from ..utils.logger import logger
from .graph_builder import build_game_graph

GRACEFUL_ERROR_STORY = (
    "A twisting mist swallows the scene before it fully forms. "
    "The world shudders, glitches, and resets — as if the dungeon itself "
    "rejected the attempt. Try again."
)


class GameOrchestrator:
    def __init__(self, output_cache: OutputCache, game_state_mgr: GameStateManager, worker_id: str = ""):
        import uuid as _uuid
        self.output_cache = output_cache
        self.game_state_mgr = game_state_mgr
        # Stable process-lifetime worker id (was f"orch-{id(self)}", collided across restarts)
        self.worker_id = worker_id or settings.app.worker_id or f"worker-{_uuid.uuid4().hex[:8]}"
        self.graph: Optional[StateGraph] = None
        self.compiled_graph = None

    async def initialize(self):
        logger.info("Initializing game orchestrator...")
        try:
            from .graph_v2 import build_game_graph_v2
            workflow = build_game_graph_v2(self.output_cache)
            logger.info("Using graph v2 (react + atomic N4)")
        except Exception as e:
            logger.warning(f"Graph v2 unavailable, fallback v1: {e}")
            workflow = build_game_graph(self.output_cache)
        self.graph = workflow
        self.compiled_graph = workflow.compile()
        logger.info("Game orchestrator initialized")

    def _build_initial_state(self, request: GameRequest) -> GameState:
        import time as _time
        import uuid as _uuid
        stats = CharacterStats()

        world = generate_world(seed=request.uuid)
        grid_data = world_to_grid_data(world)
        world_meta = world_to_meta(world)

        initial_state: GameState = {
            "uuid": request.uuid,
            "prompt": request.prompt,
            "input_data": request.data or {},
            "game_data": request.data or {"world": world_meta, "grid": world["grid"]},
            "images": {},
            "grid_data": grid_data,
            "re_description_data": None,
            "context_summary": None,
            "character_stats": stats,
            "skills": [
                Skill(
                    name="Basic Attack",
                    skill_type="attack",
                    cooldown=0,
                    max_cooldown=1,
                    level=1,
                    description="A basic melee or ranged attack",
                ),
                Skill(
                    name="Dodge",
                    skill_type="defense",
                    cooldown=0,
                    max_cooldown=2,
                    level=1,
                    description="Dodge incoming attack",
                    is_passive=False,
                ),
            ],
            "inventory": [],
            "relationships": [],
            "story_output": "",
            "decision": None,
            "needs_search": False,
            "needs_image_processing": False,
            "needs_re_description": False,
            "processed": False,
            "error": None,
            "search_results": "",
            "rag_context": "",
            "tool_results": [],
            "game_output": None,
            "conditional_passes": 0,
            "remaining_steps": settings.app.loop_recursion_limit,
            "__next__": "node4_tool_agent",
            # Re-imagined generous-local additions
            "context": "",
            "chat_log": [{"role": "user", "text": request.prompt, "turn": 0}],
            "decision_report": None,
            "budget": {"llm_calls": 0, "tokens_est": 0, "started_at": _time.time()},
            "next_node": "node4_tool_agent",
            "router_trace": [],
            "force_exit_reason": None,
            "turn_id": f"{request.uuid}:{_uuid.uuid4().hex[:8]}",
        }

        if request.images:
            from uuid import uuid4
            from ..schemas.types import ImageData
            import time
            for img in request.images:
                img_uuid = str(uuid4())
                initial_state["images"][img_uuid] = ImageData(
                    image_uuid=img_uuid,
                    game_uuid=request.uuid,
                    url=img.get("url", ""),
                    format=img.get("format", "webp"),
                    timestamp=time.time(),
                )
            initial_state["needs_image_processing"] = True

        return initial_state

    async def process_request(self, request: GameRequest) -> Optional[Dict[str, Any]]:
        logger.info(f"Processing request UUID {request.uuid}")

        if self.compiled_graph is None:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

        locked = await self.game_state_mgr.acquire_lock(request.uuid, self.worker_id)
        if not locked:
            logger.warning(f"Could not acquire lock for {request.uuid}, another worker is processing")
            return None

        try:
            existing = await self.game_state_mgr.load_state(request.uuid)
            if existing:
                logger.info(f"Loaded existing game state for {request.uuid}")
                initial_state = self._build_initial_state(request)
                # Allowlist merge (was full overwrite incl. stale budgets/flags).
                # Only long-lived fields come from persisted state; fresh request
                # fields (prompt/images/budget/turn/flags) always win.
                for k in ("character_stats", "skills", "inventory", "relationships",
                          "game_data", "context", "chat_log", "context_summary", "decision"):
                    if k in existing:
                        initial_state[k] = existing[k]
                # Append this turn's prompt to rolling chat log (cap generous local 40)
                try:
                    log = list(initial_state.get("chat_log", []) or [])
                    log.append({"role": "user", "text": request.prompt, "turn": len(log)})
                    initial_state["chat_log"] = log[-settings.app.chat_log_max_turns:]
                except Exception:
                    pass
            else:
                initial_state = self._build_initial_state(request)
                await self.game_state_mgr.save_initial_state(
                    request.uuid,
                    request.data or {},
                    initial_state.get("story_output", ""),
                )
                logger.info(f"Saved initial game state for {request.uuid}")

            result = await self._run_graph(initial_state, request.uuid)

            output = result.get("game_output")
            if output:
                story = output.get("story", "") or result.get("story_output", "")
                await self.game_state_mgr.save_state(
                    request.uuid,
                    {"game_data": output.get("game_data", {}),
                     "story": story,
                     "character_stats": output.get("game_data", {}).get("character_stats", {}),
                     "context_summary": result.get("context_summary"),
                     "decision": result.get("decision")},
                    ["game_data", "story", "character_stats", "context_summary", "decision"],
                )
                await self.game_state_mgr.try_drain(request.uuid, story)
                logger.info(f"Request {request.uuid} completed successfully")
            else:
                logger.warning(f"Request {request.uuid} completed but no output generated")

            return output

        except Exception as e:
            logger.error(
                f"Failed to process request {request.uuid}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return {
                "uuid": request.uuid,
                "error": type(e).__name__,
                "game_data": request.data,
                "story": GRACEFUL_ERROR_STORY,
            }
        finally:
            await self.game_state_mgr.release_lock(request.uuid, self.worker_id)

    async def _run_graph(self, state: GameState, uuid: str) -> Dict[str, Any]:
        """Run the graph with a wall-clock timeout and bounded recursion."""
        lock_lost: list[bool] = []

        async def _keep_lock_alive(graph_task: asyncio.Task):
            while True:
                await asyncio.sleep(settings.app.lock_refresh_interval)
                if graph_task.done():
                    return
                if not await self.game_state_mgr.refresh_lock(uuid, self.worker_id):
                    logger.warning(f"Lost lock ownership for {uuid}, aborting graph run")
                    lock_lost.append(True)
                    graph_task.cancel()
                    return

        graph_task: asyncio.Task = asyncio.create_task(
            self.compiled_graph.ainvoke(
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
