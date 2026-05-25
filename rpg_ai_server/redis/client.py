from __future__ import annotations

import json
from typing import Any, Dict, Optional

from redis.asyncio import Redis

from ..config.settings import settings
from ..utils.logger import logger


class RedisClient:
    def __init__(self, db: int, url: Optional[str] = None):
        self.db = db
        self._client: Optional[Redis] = None
        self._url = url or f"redis://{settings.redis.host}:{settings.redis.port}/{db}"

    async def connect(self):
        if self._client is None:
            self._client = await Redis.from_url(
                self._url,
                password=settings.redis.password,
                decode_responses=True,
            )
            logger.info(f"Connected to Redis DB {self.db}")

    async def disconnect(self):
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    async def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        ttl = ttl or settings.redis.ttl_seconds
        await self.connect()
        result = await self.client.setex(key, ttl, json.dumps(value))
        return bool(result)

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        await self.connect()
        data = await self.client.get(key)
        if data is None:
            return None
        return json.loads(data)

    async def delete(self, key: str) -> bool:
        await self.connect()
        return bool(await self.client.delete(key))

    async def exists(self, key: str) -> bool:
        await self.connect()
        return bool(await self.client.exists(key))

    async def memory_usage(self, key: str) -> Optional[int]:
        await self.connect()
        return await self.client.memory_usage(key)

    async def dbsize(self) -> int:
        await self.connect()
        return await self.client.dbsize()

    async def info_section(self, section: str = "memory") -> Dict[str, Any]:
        await self.connect()
        info = await self.client.info(section)
        return info

    async def memory_percent(self) -> float:
        info = await self.info_section("memory")
        used_memory = info.get("used_memory", 0)
        max_memory = info.get("maxmemory", 0)
        if max_memory == 0:
            return 0.0
        return (used_memory / max_memory) * 100.0


class InputRedisClient(RedisClient):
    def __init__(self):
        super().__init__(db=settings.redis.input_db)

    async def pop_request(self) -> Optional[Dict[str, Any]]:
        keys = await self.client.keys("*")
        if not keys:
            return None
        key = keys[0]
        data = await self.get_json(key)
        if data:
            await self.delete(key)
        return data

    async def get_all_keys(self) -> list[str]:
        return await self.client.keys("*")


class OutputRedisClient(RedisClient):
    def __init__(self):
        super().__init__(db=settings.redis.output_db)

    async def push_result(self, uuid: str, data: Dict[str, Any]) -> bool:
        return await self.set_json(uuid, data)
