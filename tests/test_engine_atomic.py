"""Engine atomicity tests: semaphore bound, poison handling, cancelable stop."""

import asyncio
import time

from rpg_ai_server.engine.multi_tasker import MultiTaskEngine


def _run(coro):
    return asyncio.run(coro)


class _Queue:
    def __init__(self):
        self.failed = []
        self.stopped = False

    async def handle_failure(self, item):
        self.failed.append(item)

    async def stop(self):
        self.stopped = True


class _Orch:
    def __init__(self, delay=0.05):
        self.delay = delay
        self.current = 0
        self.max_seen = 0

    async def process_request(self, request):
        self.current += 1
        self.max_seen = max(self.max_seen, self.current)
        try:
            await asyncio.sleep(self.delay)
            return {"ok": True}
        finally:
            self.current -= 1


def _engine(orch, permits=2):
    e = MultiTaskEngine.__new__(MultiTaskEngine)
    e.input_queue = None
    e.output_cache = None
    e.orchestrator = orch
    e.queue_mgr = _Queue()
    e._running = True
    e._active_tasks = set()
    e._semaphore = asyncio.Semaphore(permits)
    e._request_counter = 0
    e._backoff_until = 0.0
    return e


def test_concurrency_is_bounded_not_advisory():
    async def go():
        orch = _Orch()
        e = _engine(orch, permits=2)
        items = [{"uuid": f"u{i}", "prompt": "p", "data": {}, "timestamp": 0.0}
                 for i in range(5)]
        # Mirror run(): blocking acquire BEFORE create_task.
        async def launch(raw):
            await e._semaphore.acquire()
            t = asyncio.create_task(e._process_single_request(raw))
            e._active_tasks.add(t)
            t.add_done_callback(e._active_tasks.discard)
            return t

        tasks = [await launch(r) for r in items]
        await asyncio.gather(*tasks)
        return orch

    orch = _run(go())
    assert orch.max_seen <= 2, f"semaphore bypassed: {orch.max_seen} concurrent"


def test_poison_request_never_holds_slot_or_crashes():
    async def go():
        orch = _Orch(delay=0)
        e = _engine(orch, permits=1)
        before = e._semaphore._value
        await e._semaphore.acquire()
        # Missing uuid/prompt → Pydantic ValidationError inside, must DLQ + release.
        await e._process_single_request({"timestamp": 0.0})
        return e, before

    e, before = _run(go())
    assert len(e.queue_mgr.failed) == 1  # sent to retry/DLQ path, not dropped silently
    assert e._semaphore._value == before  # slot released despite parse failure


def test_stop_cancels_hanging_tasks_with_timeout():
    async def go():
        orch = _Orch(delay=60.0)
        e = _engine(orch, permits=1)
        await e._semaphore.acquire()
        t = asyncio.create_task(e._process_single_request(
            {"uuid": "u", "prompt": "p", "data": {}, "timestamp": 0.0}))
        e._active_tasks.add(t)
        await asyncio.sleep(0.05)  # let it enter orchestrator sleep
        start = time.time()
        await e.stop()
        return time.time() - start, t

    elapsed, t = _run(go())
    assert t.cancelled() or t.done()
    assert elapsed < 9.0, f"shutdown hung: {elapsed:.1f}s"


def test_stop_halts_mover_after_tasks_drain():
    async def go():
        e = _engine(_Orch(delay=0))
        await e.stop()
        return e

    e = _run(go())
    assert e.queue_mgr.stopped is True
    assert e._running is False
