"""Output cache client: result writes and counting."""
from __future__ import annotations

from typing import Any, Dict

from .base import RedisClient

class OutputRedisClient(RedisClient):
    def __init__(self):
        super().__init__(prefix="output")

    async def push_result(self, uuid: str, data: Dict[str, Any]) -> bool:
        return await self.set_json(uuid, data)

    async def count(self) -> int:
        return await self.dbsize()
