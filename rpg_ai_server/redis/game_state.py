from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .client import GamesRedisClient, RagRedisClient
from ..utils.compression import compress_text
from ..utils.logger import logger

MAJOR_ACTIONS = {"death", "level_up", "quest_complete", "boss_kill", "new_biome"}
DRAIN_THRESHOLD = 10


class GameStateManager:
    def __init__(self, games_client: GamesRedisClient, rag_client: RagRedisClient):
        self._games = games_client
        self._rag = rag_client

    async def acquire_lock(self, uuid: str, worker_id: str, ttl: int = 30) -> bool:
        return await self._games.acquire_lock(uuid, worker_id, ttl)

    async def release_lock(self, uuid: str, worker_id: str) -> bool:
        return await self._games.release_lock(uuid, worker_id)

    async def load_state(self, uuid: str) -> Optional[Dict[str, Any]]:
        raw = await self._games.hgetall(uuid)
        if raw is None:
            return None
        state: Dict[str, Any] = {}
        for field, value in raw.items():
            try:
                state[field] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                state[field] = value
        return state

    async def save_state(self, uuid: str, state: Dict[str, Any], fields: list[str]):
        for field in fields:
            value = state.get(field)
            if value is not None:
                serialized = json.dumps(value, default=str)
                await self._games.hset(uuid, field, serialized)
        await self._games.expire(uuid, 3600)

    async def save_initial_state(
        self,
        uuid: str,
        game_data: Dict[str, Any],
        story: str = "",
    ):
        await self._games.hset(uuid, "game_data", json.dumps(game_data, default=str))
        if story:
            compressed = compress_text(story)
            await self._games.hset(uuid, "story", compressed)
        await self._games.hset(uuid, "counter", "0")
        await self._games.expire(uuid, 3600)

    async def try_drain(self, uuid: str, story: str, is_major: bool = False):
        counter = await self._games.incr(uuid)
        if counter < DRAIN_THRESHOLD and not is_major and not await self._is_major_action(story):
            return False
        compressed = compress_text(story)
        payload = {"uuid": uuid, "text": compressed, "chunk_count": 1}
        await self._rag.push_staging(payload)
        await self._games.hdel(uuid, "story")
        await self._games.set_counter(uuid, 0)
        logger.info(f"Drain triggered for {uuid} (counter={counter}, major={is_major})")
        return True

    async def _is_major_action(self, story: str) -> bool:
        lower = story.lower()
        return any(kw in lower for kw in MAJOR_ACTIONS)
