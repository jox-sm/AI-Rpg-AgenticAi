from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from ..config.settings import settings
from ..redis.output_cache import OutputCache
from ..redis.queue import InputQueue, QueueManager
from ..schemas.types import GameRequest
from ..utils.logger import logger
from .orchestrator import GameOrchestrator


class MultiTaskEngine:
    def __init__(
        self,
        input_queue: InputQueue,
        output_cache: OutputCache,
        orchestrator: GameOrchestrator,
        queue_manager: QueueManager | None = None,
    ):
        self.input_queue = input_queue
        self.output_cache = output_cache
        self.orchestrator = orchestrator
        self.queue_mgr = queue_manager
        self._running = False
        self._active_tasks: set = set()
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._request_counter = 0
        self._backoff_until = 0.0

    async def start(self):
        self._running = True
        self._semaphore = asyncio.Semaphore(settings.app.max_concurrent_requests)
        if self.queue_mgr:
            await self.queue_mgr.start()
        await self.orchestrator.initialize()
        logger.info(f"Multi-task engine started (max concurrent: {settings.app.max_concurrent_requests})")

    async def stop(self):
        self._running = False
        # Snapshot: done-callbacks mutate the set during gather — never iterate live.
        tasks = list(self._active_tasks)
        if tasks:
            logger.info(f"Cancelling {len(tasks)} active tasks...")
            for t in tasks:
                t.cancel()
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("Shutdown timed out waiting for tasks, continuing")
        # Stop mover AFTER tasks: tasks may still push to the delayed queue.
        if self.queue_mgr:
            await self.queue_mgr.stop()
        logger.info("Multi-task engine stopped")

    async def _check_memory_backpressure(self) -> bool:
        if time.time() < self._backoff_until:
            remaining = self._backoff_until - time.time()
            logger.info(f"Backpressure active, waiting {remaining:.1f}s more")
            await asyncio.sleep(min(remaining, 1.0))
            return False

        memory_ok = await self.output_cache.memory_pressure_ok()
        if not memory_ok:
            logger.warning(f"Memory pressure detected, backing off for {settings.app.backoff_seconds}s")
            self._backoff_until = time.time() + settings.app.backoff_seconds
            await asyncio.sleep(settings.app.backoff_seconds)

            memory_ok = await self.output_cache.memory_pressure_ok()
            if not memory_ok:
                logger.warning("Memory still above threshold after backoff, continuing to wait")
                return False

        return True

    async def _process_single_request(self, raw_item: Dict[str, Any]):
        # Parse BEFORE semaphore: invalid payloads must not hold a slot, and
        # request must be bound before any except path touches request.uuid.
        try:
            request = GameRequest(**raw_item)
        except Exception as e:
            logger.error(f"Dropping poison request {raw_item.get('uuid', '?')}: {e}")
            if self.queue_mgr:
                await self.queue_mgr.handle_failure(raw_item)
            else:
                logger.warning("No queue manager — poison request dropped")
            self._semaphore.release()
            return
        try:
            logger.info(f"Processing request {request.uuid}")
            result = await self.orchestrator.process_request(request)
            if result is None:
                # Lock-miss: another worker owns it — requeue WITHOUT retry
                # penalty would be ideal; handle_failure counts a retry today,
                # so at minimum never lose the item. (See P06.)
                logger.warning(f"Lock not acquired for {request.uuid}, re-queuing")
                if self.queue_mgr:
                    await self.queue_mgr.handle_failure(raw_item)
            else:
                logger.info(f"Finished request {request.uuid}")
        except Exception as e:
            logger.error(f"Request {request.uuid} failed: {e}")
            if self.queue_mgr:
                await self.queue_mgr.handle_failure(raw_item)
        finally:
            self._active_tasks.discard(asyncio.current_task())
            self._semaphore.release()

    async def run(self):
        if not self._running:
            await self.start()

        logger.info("Multi-task engine entering main loop")

        while self._running:
            try:
                if self._request_counter >= 100:
                    logger.info("100 requests processed, checking memory pressure")
                    if not await self._check_memory_backpressure():
                        logger.info("Memory pressure threshold hit at check point, continuing to process existing tasks")
                    self._request_counter = 0

                if self.queue_mgr:
                    raw_item = await self.queue_mgr.next_request()
                else:
                    request = await self.input_queue.next_request()
                    raw_item = request.model_dump() if request else None

                if raw_item is None:
                    await asyncio.sleep(0.1)
                    continue

                self._request_counter += 1

                # Blocking acquire BEFORE create_task: the old advisory
                # len()-check always created the task anyway (unbounded growth).
                # The matching release lives in _process_single_request.finally.
                await self._semaphore.acquire()

                task = asyncio.create_task(self._process_single_request(raw_item))
                self._active_tasks.add(task)
                task.add_done_callback(self._active_tasks.discard)

            except asyncio.CancelledError:
                logger.info("Multi-task engine received cancellation")
                break
            except Exception as e:
                logger.error(f"Multi-task engine error: {e}")
                await asyncio.sleep(1.0)

        await self.stop()
