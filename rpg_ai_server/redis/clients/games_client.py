"""Game-state client: state hash, counters, locks, TTL touch."""
from __future__ import annotations

from typing import Any, Dict, Optional

from ...config.settings import settings
from ...utils.logger import logger
from .base import RedisClient

class GamesRedisClient(RedisClient):
    def __init__(self):
        super().__init__(prefix="games")

    async def hset(self, uuid: str, field: str, value: str) -> bool:
        await self.connect()
        await self.client.hset(self._key(f"{uuid}:state"), field, value)
        return True

    async def hget(self, uuid: str, field: str) -> Optional[str]:
        await self.connect()
        return await self.client.hget(self._key(f"{uuid}:state"), field)

    async def hgetall(self, uuid: str) -> Optional[Dict[str, str]]:
        await self.connect()
        return await self.client.hgetall(self._key(f"{uuid}:state"))

    async def hdel(self, uuid: str, field: str) -> bool:
        await self.connect()
        result = await self.client.hdel(self._key(f"{uuid}:state"), field)
        return result > 0

    async def incr(self, uuid: str) -> int:
        await self.connect()
        return await self.client.incr(self._key(f"{uuid}:counter"))

    async def set_counter(self, uuid: str, value: int, ttl: Optional[int] = None) -> bool:
        await self.connect()
        ttl = ttl or settings.redis.ttl_seconds
        await self.client.set(self._key(f"{uuid}:counter"), str(value), ex=ttl)
        return True

    async def expire(self, uuid: str, ttl: int) -> bool:
        await self.connect()
        result = await self.client.expire(self._key(f"{uuid}:state"), ttl)
        return result > 0

    async def acquire_lock(self, uuid: str, worker_id: str, ttl: int = 30) -> bool:
        await self.connect()
        result = await self.client.set(
            self._key(f"{uuid}:lock"), worker_id, nx=True, ex=ttl
        )
        return bool(result)

    async def release_lock(self, uuid: str, worker_id: str) -> bool:
        await self.connect()
        key = self._key(f"{uuid}:lock")
        lua = "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) else return 0 end"
        try:
            result = await self._eval_lua(lua, [key], [worker_id])
            return bool(result)
        except Exception as e:
            logger.warning(f"EVAL release_lock unsupported, fallback check-then-del: {e}")
            current = await self.client.get(key)
            if current == worker_id:
                await self.client.delete(key)
                return True
            return False

    async def refresh_lock(self, uuid: str, worker_id: str, ttl: int = 30) -> bool:
        await self.connect()
        key = self._key(f"{uuid}:lock")
        lua = "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('EXPIRE', KEYS[1], ARGV[2]) else return 0 end"
        try:
            result = await self._eval_lua(lua, [key], [worker_id, str(ttl)])
            return bool(result)
        except Exception as e:
            logger.warning(f"EVAL refresh_lock unsupported, fallback check-then-expire: {e}")
            current = await self.client.get(key)
            if current == worker_id:
                await self.client.expire(key, ttl)
                return True
            return False

    async def touch_game_keys(self, uuid: str, ttl: int) -> bool:
        """Atomically refresh TTL on state+counter (fixes TTL skew)."""
        await self.connect()
        lua = (
            "redis.call('EXPIRE', KEYS[1], ARGV[1]) "
            "redis.call('EXPIRE', KEYS[2], ARGV[1]) "
            "return 1"
        )
        try:
            await self._eval_lua(
                lua,
                [self._key(f"{uuid}:state"), self._key(f"{uuid}:counter")],
                [str(ttl)],
            )
            return True
        except Exception:
            await self.client.expire(self._key(f"{uuid}:state"), ttl)
            try:
                await self.client.expire(self._key(f"{uuid}:counter"), ttl)
            except Exception:
                pass
            return True
