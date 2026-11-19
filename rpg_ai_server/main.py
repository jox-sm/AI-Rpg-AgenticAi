from __future__ import annotations

import asyncio
import signal
import sys

from .engine.bootstrap import create_engine, log_startup_banner
from .utils.logger import logger


async def main():
    log_startup_banner()

    engine, clients = await create_engine()

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
        for c in clients:
            await c.disconnect()
        logger.info("D&D RPG AI Server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user (Ctrl+C)")
