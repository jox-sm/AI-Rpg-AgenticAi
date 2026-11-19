"""Input queue client: request queue, delayed/dead ZSets, heartbeats."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from ...utils.logger import logger
from .base import RedisClient

class InputRedisClient(RedisClient):
    def __init__(self):
        super().__init__(prefix="input")

    async def pop_request(self) -> Optional[Dict[str, Any]]:
        await self.connect()
        raw = await self.client.lpop(self._key("queue"))
        if raw is None:
            return None
        return json.loads(raw)

    async def push_request(self, uuid: str, data: Dict[str, Any]) -> bool:
        await self.connect()
        serialized = json.dumps(data)
        await self.client.rpush(self._key("queue"), serialized)
        return True

    async def queue_length(self) -> int:
        await self.connect()
        return await self.client.llen(self._key("queue"))

    async def push_delayed(self, item: Dict[str, Any], score: float) -> bool:
        await self.connect()
        serialized = json.dumps(item)
        await self.client.zadd(self._key("queue:delayed"), {serialized: score})
        return True

    async def pop_delayed_due(self, max_score: float) -> list[Dict[str, Any]]:
        await self.connect()
        key = self._key("queue:delayed")
        # Atomic Lua: range + rem in one step (2 procs race fix).
        lua = (
            "local items = redis.call('ZRANGEBYSCORE', KEYS[1], 0, ARGV[1]) "
            "if #items > 0 then redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1]) end "
            "return items"
        )
        try:
            raw_items = await self._eval_lua(lua, [key], [str(max_score)])
        except Exception as e:
            logger.warning(f"EVAL pop_delayed_due unsupported, fallback non-atomic: {e}")
            raw_items = await self.client.zrangebyscore(key, 0, max_score)
            if not raw_items:
                return []
            await self.client.zremrangebyscore(key, 0, max_score)
        if not raw_items:
            return []
        out = []
        for r in raw_items:
            try:
                out.append(json.loads(r))
            except Exception:
                logger.error("Poison delayed item skipped (invalid JSON)")
        return out

    async def push_dead(self, item: Dict[str, Any]):
        await self.connect()
        serialized = json.dumps(item)
        score = item.get("timestamp", 0)
        await self.client.zadd(self._key("queue:dead"), {serialized: score})

    async def set_heartbeat(self, worker_id: str, game_uuid: str, ttl: int = 15) -> bool:
        await self.connect()
        await self.client.set(self._key(f"workers:{worker_id}:heartbeat"), game_uuid, ex=ttl)
        return True

    async def get_heartbeat(self, worker_id: str) -> Optional[str]:
        await self.connect()
        return await self.client.get(self._key(f"workers:{worker_id}:heartbeat"))

    async def get_all_keys(self) -> list[str]:
        return await self.keys("*")
