"""Combined service entrypoint: gameplay HTTP API + in-process LangGraph engine.

Run modes (exactly one instance should own the engine — per-game Redis locks
make two engines safe, but wasteful):

    python -m uvicorn rpg_ai_server.api:app --port 8000        # API + engine
    python -m uvicorn rpg_ai_server.redis_api:app --port 8000   # API only (tests)
    python -m rpg_ai_server.main                                 # engine only

Implementation note: `api.py` reuses the single `redis_api.app` instance and
appends engine lifecycle handlers to it, so both uvicorn targets stay correct
and the router is included exactly once:

    redis_api:app → API only (no engine)
    api:app       → the same app + engine handlers registered below
"""

from __future__ import annotations

import asyncio

from . import redis_api
from .engine.bootstrap import create_engine, log_startup_banner
from .utils.logger import logger

app = redis_api.app
app.title = "RPG AI Server (gameplay API + engine)"

_engine_task: asyncio.Task | None = None
_engine_clients: list = []


@app.on_event("startup")
async def start_engine():
    global _engine_task, _engine_clients
    log_startup_banner()
    engine, _engine_clients = await create_engine()
    await engine.start()
    _engine_task = asyncio.create_task(engine.run())
    logger.info("Combined service up: gameplay API + engine in one process")


@app.on_event("shutdown")
async def stop_engine():
    global _engine_task, _engine_clients
    logger.info("Shutting down combined service engine...")
    if _engine_task is not None and not _engine_task.done():
        _engine_task.cancel()
        try:
            await _engine_task
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
    for c in _engine_clients:
        await c.disconnect()
    _engine_task = None
    _engine_clients = []
    logger.info("D&D RPG AI Server stopped")
