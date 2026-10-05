from __future__ import annotations

import asyncio
import signal
import sys

from .config.settings import settings
from .engine.multi_tasker import MultiTaskEngine
from .engine.orchestrator import GameOrchestrator
from .redis.client import InputRedisClient, OutputRedisClient, GamesRedisClient
from .redis.game_state import GameStateManager
from .redis.queue import InputQueue
from .redis.output_cache import OutputCache
from .redis.queue import QueueManager
from .redis.vector_memory import GameMemory
from .utils.logger import logger


async def main():
    logger.info("=" * 60)
    logger.info("D&D RPG AI Server Starting")
    logger.info(f"Max concurrent requests: {settings.app.max_concurrent_requests}")
    logger.info(f"Output memory threshold: {settings.app.output_memory_threshold}%")
    logger.info(f"Redis input DB: {settings.redis.input_db}, output DB: {settings.redis.output_db}")
    if settings.search.configured:
        logger.info(f"Search memory: configured (index={settings.search.index_name})")
    else:
        logger.warning("Search memory: UPSTASH_SEARCH_REST_URL/TOKEN missing — memory drain disabled")
    logger.info("=" * 60)

    input_client = InputRedisClient()
    output_client = OutputRedisClient()
    games_client = GamesRedisClient()

    await input_client.connect()
    await output_client.connect()
    await games_client.connect()
    logger.info("Redis connections established")

    input_queue = InputQueue(input_client)
    output_cache = OutputCache(output_client)
    game_state_mgr = GameStateManager(games_client, memory=GameMemory())
    queue_mgr = QueueManager(input_client)
    orchestrator = GameOrchestrator(output_cache, game_state_mgr, worker_id=queue_mgr._worker_id)

    engine = MultiTaskEngine(
        input_queue=input_queue,
        output_cache=output_cache,
        orchestrator=orchestrator,
        queue_manager=queue_mgr,
    )

    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        sigs = [signal.SIGINT, signal.SIGTERM]
        if sys.platform == "win32" and hasattr(signal, "SIGBREAK"):
            sigs.append(signal.SIGBREAK)
        try:
            for sig in sigs:
                loop.add_signal_handler(sig, _signal_handler)
        except (NotImplementedError, AttributeError, RuntimeError, ValueError):
            # Windows ProactorEventLoop: no add_signal_handler — Ctrl+C still
            # arrives as KeyboardInterrupt/CancelledError, handled below.
            logger.warning("Signal handlers not supported on this platform — Ctrl+C stays graceful via KeyboardInterrupt")

    engine_task = None
    try:
        await engine.start()
        engine_task = asyncio.create_task(engine.run())

        await shutdown_event.wait()

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown requested (Ctrl+C) — stopping...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        if engine_task is not None and not engine_task.done():
            logger.info("Shutting down...")
            engine_task.cancel()
            try:
                await engine_task
            except (asyncio.CancelledError, KeyboardInterrupt):
                pass
        await input_client.disconnect()
        await output_client.disconnect()
        await games_client.disconnect()
        logger.info("D&D RPG AI Server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user (Ctrl+C)")