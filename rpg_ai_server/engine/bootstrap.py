"""Shared engine bootstrap.

Used by both the standalone engine process (``python -m rpg_ai_server.main``)
and the combined API+engine service (``uvicorn rpg_ai_server.api:app``) so
exactly one code path assembles Redis clients → queue/state caches → engine.
"""

from __future__ import annotations

from rpg_ai_server.config.settings import settings
from rpg_ai_server.engine.multi_tasker import MultiTaskEngine
from rpg_ai_server.engine.orchestrator import GameOrchestrator
from rpg_ai_server.redis.client import GamesRedisClient, InputRedisClient, OutputRedisClient
from rpg_ai_server.redis.game_state import GameStateManager
from rpg_ai_server.redis.output_cache import OutputCache
from rpg_ai_server.redis.queue import InputQueue, QueueManager
from rpg_ai_server.redis.vector_memory import GameMemory
from rpg_ai_server.utils.logger import logger

EngineClients = list[InputRedisClient | GamesRedisClient | OutputRedisClient]


async def create_engine() -> tuple[MultiTaskEngine, EngineClients]:
    """Connect the Redis trio and assemble the engine.

    Returns the engine (not yet started) and the connected clients so the
    caller can disconnect them on shutdown.
    """
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
    return engine, [input_client, output_client, games_client]


def log_startup_banner() -> None:
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
