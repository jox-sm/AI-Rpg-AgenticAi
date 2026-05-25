from __future__ import annotations

import asyncio
import signal
import sys

from .config.settings import settings
from .engine.multi_tasker import MultiTaskEngine
from .engine.orchestrator import GameOrchestrator
from .redis.client import InputRedisClient, OutputRedisClient
from .redis.input_queue import InputQueue
from .redis.output_cache import OutputCache
from .utils.logger import logger


async def main():
    logger.info("=" * 60)
    logger.info("D&D RPG AI Server Starting")
    logger.info(f"Max concurrent requests: {settings.app.max_concurrent_requests}")
    logger.info(f"Output memory threshold: {settings.app.output_memory_threshold}%")
    logger.info(f"Redis input DB: {settings.redis.input_db}, output DB: {settings.redis.output_db}")
    logger.info("=" * 60)

    input_client = InputRedisClient()
    output_client = OutputRedisClient()

    await input_client.connect()
    await output_client.connect()
    logger.info("Redis connections established")

    input_queue = InputQueue(input_client)
    output_cache = OutputCache(output_client)
    orchestrator = GameOrchestrator(output_cache)

    engine = MultiTaskEngine(
        input_queue=input_queue,
        output_cache=output_cache,
        orchestrator=orchestrator,
    )

    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)
    except (NotImplementedError, AttributeError):
        logger.warning("Signal handlers not supported on this platform, using poll-based shutdown detection")

    try:
        await engine.start()
        engine_task = asyncio.create_task(engine.run())

        await shutdown_event.wait()

        logger.info("Shutting down...")
        engine_task.cancel()
        try:
            await engine_task
        except asyncio.CancelledError:
            pass

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await input_client.disconnect()
        await output_client.disconnect()
        logger.info("D&D RPG AI Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
