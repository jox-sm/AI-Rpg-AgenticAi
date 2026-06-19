from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from .client import InputRedisClient
from ..schemas.types import GameRequest
from ..utils.logger import logger


class InputQueue:
    def __init__(self, client: InputRedisClient):
        self._client = client

    async def next_request(self) -> Optional[GameRequest]:
        try:
            raw = await self._client.pop_request()
            if raw is None:
                return None
            return GameRequest(**raw)
        except Exception as e:
            logger.error(f"Failed to pop request from input queue: {e}")
            return None

    async def enqueue(self, request: GameRequest):
        await self._client.push_request(request.uuid, request.model_dump())

    async def requeue(self, request: GameRequest):
        await self._client.set_json(request.uuid, request.model_dump())

    async def queue_size(self) -> int:
        return await self._client.queue_length()
