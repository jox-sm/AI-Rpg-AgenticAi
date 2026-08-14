import asyncio
import json
import time

import pytest

from rpg_ai_server.redis.queue import DELAY_BASE, MAX_RETRIES, QueueManager, backoff_delay
from tests.fakes import FakeInputClient


def _run(coro):
    return asyncio.run(coro)


def test_backoff_delay_values():
    assert backoff_delay(0) == DELAY_BASE
    assert backoff_delay(1) == DELAY_BASE * 2
    assert backoff_delay(2) == DELAY_BASE * 4
    assert backoff_delay(3) == DELAY_BASE * 8


def test_next_request_adds_defaults():
    client = FakeInputClient()
    client.queue.append(json.dumps({"uuid": "u1", "data": {}}))
    mgr = QueueManager(client)

    item = _run(mgr.next_request())
    assert item["uuid"] == "u1"
    assert item["retry_count"] == 0
    assert item["max_retries"] == MAX_RETRIES
    assert "timestamp" in item


def test_next_request_empty_returns_none():
    mgr = QueueManager(FakeInputClient())
    assert _run(mgr.next_request()) is None


def test_failure_moves_to_delayed_then_dead():
    client = FakeInputClient()
    mgr = QueueManager(client)
    now = time.time()
    base = {"uuid": "u1", "data": {}, "max_retries": MAX_RETRIES, "timestamp": now}

    _run(mgr.handle_failure({**base, "retry_count": 0}))
    _run(mgr.handle_failure({**base, "retry_count": 1}))

    assert len(client.delayed) == 2
    assert len(client.dead) == 0

    _run(mgr.handle_failure({**base, "retry_count": 2}))

    # earlier failures stay scheduled in the delayed queue; only the last one dies
    assert len(client.delayed) == 2
    assert len(client.dead) == 1


def test_failure_respects_custom_max_retries():
    client = FakeInputClient()
    mgr = QueueManager(client)
    item = {"uuid": "u1", "data": {}, "retry_count": 0, "max_retries": 1, "timestamp": time.time()}

    _run(mgr.handle_failure(item))
    assert len(client.delayed) == 0
    assert len(client.dead) == 1


def test_delayed_scores_increase_exponentially():
    client = FakeInputClient()
    mgr = QueueManager(client)
    now = time.time()

    _run(mgr.handle_failure({"uuid": "u1", "retry_count": 0, "max_retries": 3, "timestamp": now}))
    _run(mgr.handle_failure({"uuid": "u1", "retry_count": 1, "max_retries": 3, "timestamp": now}))

    scores = sorted(client.delayed.values())
    assert len(scores) == 2
    assert scores[1] > scores[0]
    assert scores[1] - scores[0] == pytest.approx(10, abs=0.2)


def test_pop_delayed_due_only_returns_ready_items():
    client = FakeInputClient()
    now = time.time()
    item1 = {"uuid": "u1"}
    item2 = {"uuid": "u2"}
    _run(client.push_delayed(item1, now - 1))
    _run(client.push_delayed(item2, now + 60))

    due = _run(client.pop_delayed_due(now))
    assert [d["uuid"] for d in due] == ["u1"]
    assert len(client.delayed) == 1


def test_heartbeat_records_worker():
    client = FakeInputClient()
    mgr = QueueManager(client)
    _run(mgr.heartbeat("game-1"))
    assert len(client.heartbeats) == 1
    worker_id, game = client.heartbeats[0]
    assert worker_id.startswith("worker-")
    assert game == "game-1"
