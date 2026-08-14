import asyncio

from rpg_ai_server.redis.game_state import DRAIN_THRESHOLD, GameStateManager
from rpg_ai_server.redis.vector_memory import GameMemory
from tests.fakes import FakeGamesClient, FakeSearchIndex


def _run(coro):
    return asyncio.run(coro)


def _docs(mem, sid):
    return [d for d in mem._index.data.values() if d.metadata.get("sid") == sid]


def _make_manager(memory=True):
    games = FakeGamesClient()
    mem = GameMemory(index=FakeSearchIndex()) if memory else None
    return games, mem, GameStateManager(games, memory=mem)


def test_save_and_load_state_roundtrip():
    games, _, mgr = _make_manager()
    state = {"game_data": {"hp": 10}, "story": "A tale.", "context_summary": {"foo": "bar"}}

    _run(mgr.save_state("u1", state, ["game_data", "story", "context_summary"]))

    loaded = _run(mgr.load_state("u1"))
    assert loaded == state
    assert ("u1", 3600) in games.expires


def test_load_state_missing_returns_none():
    _, _, mgr = _make_manager()
    assert _run(mgr.load_state("missing")) is None


def test_save_initial_state():
    games, _, mgr = _make_manager()
    _run(mgr.save_initial_state("u1", {"hp": 1}, story="Once upon a time..."))
    assert games.hashes["u1"]["counter"] == "0"
    assert games.hashes["u1"]["game_data"] is not None


def test_drain_below_threshold_does_not_upsert():
    games, mem, mgr = _make_manager()
    for _ in range(DRAIN_THRESHOLD - 1):
        _run(mgr.try_drain("u1", "Small story."))
    assert not mem._index.data
    assert games.counters["u1"] == DRAIN_THRESHOLD - 1


def test_drain_at_threshold_upserts_to_search():
    games, mem, mgr = _make_manager()
    _run(mgr.save_state("u1", {"story": "Small story."}, ["story"]))
    for _ in range(DRAIN_THRESHOLD):
        _run(mgr.try_drain("u1", "Small story."))
    assert _docs(mem, "u1")
    assert games.counters["u1"] == 0
    assert "story" not in games.hashes.get("u1", {})


def test_drain_major_action_upserts_immediately():
    games, mem, mgr = _make_manager()
    _run(mgr.save_state("u1", {"story": "A level_up happened!"}, ["story"]))
    ok = _run(mgr.try_drain("u1", "A level_up happened!", is_major=True))
    assert ok is True
    assert _docs(mem, "u1")
    assert games.counters["u1"] == 0


def test_drain_detects_major_action_in_text():
    games, mem, mgr = _make_manager()
    ok = _run(mgr.try_drain("u1", "The boss died. A quest_complete unfolds."))
    assert ok is True
    assert _docs(mem, "u1")


def test_drain_marks_incident_metadata():
    _, mem, mgr = _make_manager()
    _run(mgr.try_drain("u1", "A level_up happened.", is_major=True))
    doc = _docs(mem, "u1")[0]
    assert doc.metadata["is_incident"] is True
    assert doc.metadata["sid"] == "u1"
    assert doc.metadata["turn"] == 1


def test_drain_without_memory_keeps_story():
    games, _, mgr = _make_manager(memory=False)
    _run(mgr.save_state("u1", {"story": "Small story."}, ["story"]))
    for _ in range(DRAIN_THRESHOLD):
        _run(mgr.try_drain("u1", "Small story."))
    assert "story" in games.hashes.get("u1", {})


def test_drain_when_memory_fails_keeps_story():
    games, _, mgr = _make_manager()

    class BoomIndex:
        data = {}
        deleted = []

        def upsert(self, documents):
            raise RuntimeError("search blew up")

    mgr._memory = GameMemory(index=BoomIndex())

    _run(mgr.save_state("u1", {"story": "Small story."}, ["story"]))
    for _ in range(DRAIN_THRESHOLD):
        _run(mgr.try_drain("u1", "Small story."))
    assert "story" in games.hashes.get("u1", {})
    assert not BoomIndex.data


def test_drain_empty_story_clears_buffer():
    games, mem, mgr = _make_manager()
    for _ in range(DRAIN_THRESHOLD):
        _run(mgr.try_drain("u1", ""))
    assert not _docs(mem, "u1")


def test_lock_lifecycle_and_refresh():
    games, _, mgr = _make_manager()
    assert _run(mgr.acquire_lock("u1", "worker")) is True
    assert _run(mgr.acquire_lock("u1", "other")) is False
    assert _run(mgr.refresh_lock("u1", "worker")) is True
    assert _run(mgr.refresh_lock("u1", "intruder")) is False
    assert _run(mgr.release_lock("u1", "intruder")) is False
    assert _run(mgr.release_lock("u1", "worker")) is True
