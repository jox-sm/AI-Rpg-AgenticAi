"""Orchestrator correctness: allowlist merge + lock-loss abort. Scrape: no network."""

import asyncio
import json

import pytest

import rpg_ai_server.agents.node1_web_search as n1
from rpg_ai_server.config.settings import settings
from rpg_ai_server.engine.orchestrator import GRACEFUL_ERROR_STORY, GameOrchestrator
from rpg_ai_server.redis.game_state import GameStateManager
from rpg_ai_server.schemas.types import GameRequest
from tests.fakes import FakeGamesClient, FakeOutputClient


def _run(coro):
    return asyncio.run(coro)


class _StubGraph:
    def __init__(self, result=None, delay=0.0):
        self.result = result or {"game_output": {"uuid": "u", "story": "s", "game_data": {}}}
        self.seen = None
        self.delay = delay

    async def ainvoke(self, state, config=None):
        self.seen = state
        if self.delay:
            await asyncio.sleep(self.delay)
        return self.result


def _orch(games, graph, memory=None):
    from rpg_ai_server.redis.output_cache import OutputCache
    o = GameOrchestrator(OutputCache(FakeOutputClient()),
                         GameStateManager(games, memory=memory),
                         worker_id="w-test")
    o.compiled_graph = graph
    return o


def test_merge_keeps_persisted_stats_but_fresh_budget_and_prompt():
    games = FakeGamesClient()
    games.hashes["u9"] = {
        "remaining_steps": json.dumps(11),          # stale, near-exhausted
        "needs_search": json.dumps(True),           # stale reroute flag
        "character_stats": json.dumps({"level": 9}),
        "prompt": json.dumps("old prompt"),
    }
    graph = _StubGraph()
    o = _orch(games, graph)
    out = _run(o.process_request(GameRequest(uuid="u9", prompt="new prompt")))
    assert out is not None
    seen = graph.seen
    assert seen["prompt"] == "new prompt"                       # fresh wins
    assert seen["remaining_steps"] == settings.app.loop_recursion_limit  # not 11
    assert seen["needs_search"] is False                        # not stale True
    assert seen["character_stats"] == {"level": 9}               # persisted kept
    assert seen["turn_id"].startswith("u9:")                    # idempotency key


def test_lock_loss_aborts_graph_but_engine_survives(monkeypatch):
    monkeypatch.setattr(settings.app, "lock_refresh_interval", 0.01)

    class FlakyLock(FakeGamesClient):
        async def refresh_lock(self, uuid, worker_id, ttl=30):
            return False  # stolen immediately

    games = FlakyLock()
    graph = _StubGraph(delay=60.0)
    o = _orch(games, graph)
    import time
    t0 = time.time()
    out = _run(o.process_request(GameRequest(uuid="uL", prompt="p")))
    elapsed = time.time() - t0
    assert out["story"] == GRACEFUL_ERROR_STORY  # graceful, NOT CancelledError
    assert out["error"] == "TimeoutError"        # converted, engine keeps running
    assert elapsed < 5.0
    assert "uL" not in games.locks                # released in finally


def test_lore_scrape_uses_cacheable_sources_without_network(monkeypatch):
    calls = []

    async def fake_fetch(url, timeout):
        calls.append(url)
        assert "User-Agent" not in url
        return "Lore text about beholders. " * 10  # >= 80 chars: passes quality gate

    async def no_network(url, timeout):
        raise AssertionError(f"network hit (must stay offline): {url}")

    monkeypatch.setattr(n1, "_fetch_and_extract", fake_fetch)
    monkeypatch.setattr(n1, "_fetch_html", no_network)
    out = _run(n1.node1_web_search({
        "uuid": "u", "prompt": "tell me",
        "decision_report": {"search_query": "beholder"},
    }))
    assert "beholders" in out["search_results"]
    assert out["needs_search"] is False
    assert len(calls) == 1 and "beholder" in calls[0]  # direct wiki guess, no DDG fallback
