from __future__ import annotations

from typing import Any, Dict, Optional

from .client import OutputRedisClient
from ..config.settings import settings
from ..schemas.types import GameOutput
from ..utils.logger import logger


class OutputCache:
    def __init__(self, client: OutputRedisClient):
        self._client = client

    async def store_result(self, output: GameOutput) -> bool:
        try:
            result = await self._client.push_result(
                output.uuid,
                output.model_dump(),
            )
            logger.info(f"Stored result for UUID {output.uuid}")
            return result
        except Exception as e:
            logger.error(f"Failed to store result for UUID {output.uuid}: {e}")
            return False

    async def memory_pressure_ok(self) -> bool:
        try:
            percent = await self._client.memory_percent()
            is_ok = percent < settings.app.output_memory_threshold
            if not is_ok:
                logger.warning(f"Output Redis memory at {percent:.1f}% (threshold: {settings.app.output_memory_threshold}%)")
            return is_ok
        except Exception as e:
            logger.warning(f"Cannot check Redis memory (likely no maxmemory set): {e}")
            return True

    async def count(self) -> int:
        return await self._client.dbsize()
