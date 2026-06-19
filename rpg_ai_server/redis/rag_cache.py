from __future__ import annotations

from typing import Any, Dict, Optional

from .client import RagRedisClient
from ..utils.logger import logger


class RagCache:
    def __init__(self, client: RagRedisClient):
        self._client = client

    async def next_staging(self) -> Optional[Dict[str, Any]]:
        try:
            return await self._client.pop_staging()
        except Exception as e:
            logger.error(f"Failed to pop RAG staging item: {e}")
            return None

    async def get_chunk(self, uuid: str, index: int) -> Optional[Dict[str, Any]]:
        try:
            return await self._client.get_chunk(uuid, index)
        except Exception as e:
            logger.error(f"Failed to get RAG chunk {uuid}:{index}: {e}")
            return None

    async def staging_count(self) -> int:
        try:
            return await self._client.staging_count()
        except Exception as e:
            logger.error(f"Failed to get RAG staging count: {e}")
            return 0
