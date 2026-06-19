from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from .client import InputRedisClient
from ..utils.logger import logger

MAX_RETRIES = 3
DELAY_BASE = 5


def backoff_delay(retry_count: int) -> float:
    return DELAY_BASE * (2 ** retry_count)


class QueueManager:
    def __init__(self, client: InputRedisClient):
        self._client = client
        self._worker_id = f"worker-{id(self)}"
        self._mover_task: Optional[asyncio.Task] = None

    async def start(self):
        self._mover_task = asyncio.create_task(self._mover_loop())
        logger.info(f"QueueManager started (worker={self._worker_id})")

    async def stop(self):
        if self._mover_task:
            self._mover_task.cancel()
            try:
                await self._mover_task
            except asyncio.CancelledError:
                pass
            self._mover_task = None

    async def next_request(self) -> Optional[Dict[str, Any]]:
        item = await self._client.pop_request()
        if item is None:
            return None
        if "retry_count" not in item:
            item["retry_count"] = 0
            item["max_retries"] = MAX_RETRIES
            item["timestamp"] = time.time()
        return item

    async def handle_failure(self, item: Dict[str, Any]):
        retry_count = item.get("retry_count", 0) + 1
        item["retry_count"] = retry_count
        item["last_error_time"] = time.time()

        if retry_count < item.get("max_retries", MAX_RETRIES):
            delay = backoff_delay(retry_count)
            score = time.time() + delay
            await self._client.push_delayed(item, score)
            logger.info(
                f"Queued {item.get('uuid', '?')} to delayed queue "
                f"(retry={retry_count}/{item.get('max_retries', MAX_RETRIES)}, "
                f"delay={delay:.0f}s)"
            )
        else:
            await self._client.push_dead(item)
            logger.warning(
                f"Request {item.get('uuid', '?')} moved to dead letter queue "
                f"(retries exhausted)"
            )

    async def heartbeat(self, game_uuid: str):
        await self._client.set_heartbeat(self._worker_id, game_uuid)

    async def _mover_loop(self):
        while True:
            try:
                items = await self._client.pop_delayed_due(time.time())
                for item in items:
                    await self._client.push_request(item.get("uuid", ""), item)
                    logger.debug(f"Moved delayed item {item.get('uuid', '?')} back to queue")
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Mover error: {e}")
                await asyncio.sleep(1)
