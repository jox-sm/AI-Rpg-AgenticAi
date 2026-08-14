import asyncio

from rpg_ai_server.redis.vector_memory import GameMemory
from tests.fakes import FakeSearchIndex


def _run(coro):
    return asyncio.run(coro)


def _memory():
    return GameMemory(index=FakeSearchIndex())


def _docs(mem, sid):
    return [d for d in mem._index.data.values() if d.metadata.get("sid") == sid]


def test_upsert_chunks_returns_count_and_stores_documents():
    mem = _memory()
    n = _run(mem.upsert_chunks("game-1", ["Hello world.", "Dragons rule."], turn=2))
    assert n == 2
    docs = _docs(mem, "game-1")
    assert len(docs) == 2
    metas = {d.metadata["index"]: d for d in docs}
    assert all(m["sid"] == "game-1" and m["turn"] == 2 for m in (d.metadata for d in docs))
    assert metas[0].content["text"] == "Hello world."
    assert all(d.id.startswith("game-1:2:") for d in docs)


def test_upsert_chunks_empty_is_noop():
    mem = _memory()
    assert _run(mem.upsert_chunks("game-1", [])) == 0
    assert not mem._index.data


def test_upsert_accepts_plain_text_documents():
    mem = _memory()
    n = _run(mem.upsert("game-1", [{"id": "game-1:custom", "text": "Plain text.", "metadata": {"turn": 9}}]))
    assert n == 1
    doc = mem._index.data["game-1:custom"]
    assert doc.metadata["sid"] == "game-1"
    assert doc.metadata["turn"] == 9
    assert doc.content["text"] == "Plain text."


def test_upsert_skips_invalid_documents():
    mem = _memory()
    n = _run(mem.upsert("game-1", [{"id": "a"}, {"id": "b", "content": {"text": "ok"}}]))
    assert n == 1
    assert "b" in mem._index.data


def test_query_ranks_by_relevance_scoped_to_sid():
    mem = _memory()
    _run(mem.upsert_chunks("game-1", ["The goblin king attacks with a rusty axe.", "You find a healing potion.", "A dragon sleeps on gold."]))
    _run(mem.upsert_chunks("game-2", ["The goblin king of another realm."]))
    results = _run(mem.query("game-1", "goblin king axe"))
    assert results
    assert all("score" in r and "content" in r and "metadata" in r for r in results)
    assert all(r["metadata"]["sid"] == "game-1" for r in results)
    assert results[0]["content"]["text"].startswith("The goblin king")


def test_query_empty_text_returns_empty():
    mem = _memory()
    assert _run(mem.query("game-1", "   ")) == []


def test_query_top_k_respected():
    mem = _memory()
    _run(mem.upsert_chunks("game-1", ["alpha one", "beta two three", "gamma"], turn=1))
    results = _run(mem.query("game-1", "alpha", top_k=1))
    assert len(results) == 1
    assert "alpha" in results[0]["content"]["text"]


def test_export_dumps_all_content_and_metadata():
    mem = _memory()
    texts = [f"Memory chunk number {i} of the grimoire." for i in range(5)]
    _run(mem.upsert_chunks("game-1", texts, turn=3))
    items = _run(mem.export("game-1"))
    assert len(items) == 5
    assert all(i["content"] and "text" in i["content"] for i in items)
    assert all(i["metadata"]["turn"] == 3 for i in items)


def test_export_ignores_other_games():
    mem = _memory()
    _run(mem.upsert_chunks("game-1", ["One."]))
    _run(mem.upsert_chunks("game-2", ["Two."]))
    items = _run(mem.export("game-1"))
    assert len(items) == 1
    assert "One." in items[0]["content"]["text"]


def test_export_missing_sid_is_empty():
    mem = _memory()
    assert _run(mem.export("nope")) == []


def test_export_restore_roundtrip():
    mem = _memory()
    texts = [f"Memory {i} about goblins and gold." for i in range(10)]
    _run(mem.upsert_chunks("game-1", texts, turn=5))
    exported = _run(mem.export("game-1"))
    ids_before = {i["id"] for i in exported}

    _run(mem.clear("game-1"))
    assert _run(mem.export("game-1")) == []

    restored = _run(mem.restore("game-1", exported))
    assert restored == 10
    ids_after = {i["id"] for i in _run(mem.export("game-1"))}
    assert ids_after == ids_before


def test_restore_empty_is_noop():
    mem = _memory()
    assert _run(mem.restore("game-1", [])) == 0


def test_clear_deletes_only_that_sid():
    mem = _memory()
    _run(mem.upsert_chunks("game-1", ["Text."]))
    _run(mem.upsert_chunks("game-2", ["Other."]))
    assert _run(mem.clear("game-1")) is True
    assert _docs(mem, "game-1") == []
    assert len(_docs(mem, "game-2")) == 1