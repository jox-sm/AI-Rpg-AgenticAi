from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .client import GamesRedisClient
from .vector_memory import GameMemory, split_into_chunks
from ..config.settings import settings
from ..utils.compression import compress_text
from ..utils.logger import logger

MAJOR_ACTIONS = {"death", "level_up", "quest_complete", "boss_kill", "new_biome"}
DRAIN_THRESHOLD = 10


class GameStateManager:
    def __init__(self, games_client: GamesRedisClient, memory: Optional[GameMemory] = None):
        self._games = games_client
        self._memory = memory

    async def acquire_lock(self, uuid: str, worker_id: str, ttl: int | None = None) -> bool:
        ttl = ttl or settings.app.lock_ttl_seconds
        return await self._games.acquire_lock(uuid, worker_id, ttl)

    async def release_lock(self, uuid: str, worker_id: str) -> bool:
        return await self._games.release_lock(uuid, worker_id)

    async def refresh_lock(self, uuid: str, worker_id: str, ttl: int | None = None) -> bool:
        ttl = ttl or settings.app.lock_ttl_seconds
        return await self._games.refresh_lock(uuid, worker_id, ttl)

    async def load_state(self, uuid: str) -> Optional[Dict[str, Any]]:
        raw = await self._games.hgetall(uuid)
        if not raw:
            return None
        state: Dict[str, Any] = {}
        for field, value in raw.items():
            try:
                state[field] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Fallback: try decompressed legacy story blob, else raw string
                try:
                    from ..utils.compression import decompress_text
                    dec = decompress_text(value) if field == "story" else None
                    state[field] = dec if dec is not None else value
                except Exception:
                    state[field] = value
        return state

    async def save_state(self, uuid: str, state: Dict[str, Any], fields: list[str]):
        for field in fields:
            value = state.get(field)
            if value is not None:
                serialized = json.dumps(value, default=str)
                await self._games.hset(uuid, field, serialized)
        # Refresh both state+counter TTL atomically (fixes skew)
        await self._games.touch_game_keys(uuid, settings.redis.ttl_seconds)

    async def save_initial_state(
        self,
        uuid: str,
        game_data: Dict[str, Any],
        story: str = "",
        chat_log: Optional[list] = None,
        context: str = "",
    ):
        await self._games.hset(uuid, "game_data", json.dumps(game_data, default=str))
        if story:
            compressed = compress_text(story)
            await self._games.hset(uuid, "story", compressed)
        # Rolling memory the allowlist merge reads back — previously never written,
        # so chat_log/context reset every turn. Both are capped upstream.
        if chat_log:
            await self._games.hset(uuid, "chat_log", json.dumps(chat_log, default=str))
        if context:
            await self._games.hset(uuid, "context", json.dumps(context, default=str))
        # Single string counter with TTL (was hash-field split-brain)
        await self._games.set_counter(uuid, 0)
        await self._games.expire(uuid, settings.redis.ttl_seconds)

    async def try_drain(self, uuid: str, story: str, is_major: bool = False):
        """Move the running story buffer into vector memory once it overflows.

        Vectors are never deleted on drain — only exported to the game's
        Upstash Vector namespace; the Redis story field is cleared to keep
        the state hash small. Runs under the per-game lock (Lua-safe), so
        only one worker drains at a time.
        """
        threshold = settings.app.drain_threshold
        counter = await self._games.incr(uuid)
        # Keep counter TTL fresh alongside state
        await self._games.touch_game_keys(uuid, settings.redis.ttl_seconds)
        if counter < threshold and not is_major and not await self._is_major_action(story):
            return False
        if self._memory is None:
            logger.warning(f"No vector memory configured, keeping story buffer for {uuid}")
            return False
        chunks = split_into_chunks(story)
        if not chunks:
            await self._games.hdel(uuid, "story")
            await self._games.set_counter(uuid, 0)
            return False
        try:
            await self._memory.upsert_chunks(uuid, chunks, turn=counter, is_incident=is_major)
        except Exception as e:
            logger.error(f"Drain failed for {uuid}: {e}")
            return False
        await self._games.hdel(uuid, "story")
        await self._games.set_counter(uuid, 0)
        logger.info(f"Drained {len(chunks)} chunk(s) for {uuid} to vector memory (counter={counter}, major={is_major})")
        return True

    async def _is_major_action(self, story: str) -> bool:
        lower = story.lower()
        return any(kw in lower for kw in MAJOR_ACTIONS)