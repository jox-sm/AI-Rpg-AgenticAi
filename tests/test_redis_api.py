import asyncio
import json

import httpx
import pytest

from rpg_ai_server import redis_api
from rpg_ai_server.redis.vector_memory import GameMemory
from tests.fakes import FakeGamesClient, FakeInputClient, FakeOutputClient, FakeSearchIndex


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def client(monkeypatch):
    memory = GameMemory(index=FakeSearchIndex())
    monkeypatch.setattr(redis_api, "_memory", memory)
    monkeypatch.setattr(redis_api, "_games", FakeGamesClient())
    monkeypatch.setattr(redis_api, "_output", FakeOutputClient())
    monkeypatch.setattr(redis_api, "_input", FakeInputClient())
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=redis_api.app),
        base_url="http://test",
    )


@pytest.mark.anyio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_memory_upsert_then_export(client):
    documents = [
        {"id": f"game-1:{i}", "content": {"text": f"The party fights goblin number {i} in the cave."}, "metadata": {"sid": "game-1"}}
        for i in range(5)
    ]
    resp = await client.post("/memory/upsert", json={"namespace": "game-1", "documents": documents})
    assert resp.status_code == 200
    assert resp.json()["chunks"] == 5

    resp = await client.get("/memory/export/game-1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sid"] == "game-1"
    assert "saved_at" in body and "chunks" in body
    assert len(body["chunks"]) == 5


@pytest.mark.anyio
async def test_memory_upsert_empty_documents(client):
    resp = await client.post("/memory/upsert", json={"namespace": "game-1", "documents": []})
    assert resp.status_code == 200
    assert resp.json()["chunks"] == 0


@pytest.mark.anyio
async def test_memory_query_hits(client):
    documents = [
        {"id": "game-1:0", "content": {"text": "A goblin king wields a rusty axe."}, "metadata": {"sid": "game-1"}},
        {"id": "game-1:1", "content": {"text": "You discover a healing potion."}, "metadata": {"sid": "game-1"}},
    ]
    await client.post("/memory/upsert", json={"namespace": "game-1", "documents": documents})

    resp = await client.post("/memory/query", json={"namespace": "game-1", "query": "goblin axe", "top_k": 1})
    assert resp.status_code == 200
    hits = resp.json()["hits"]
    assert len(hits) == 1
    assert hits[0]["score"] > 0
    assert "goblin" in hits[0]["content"]["text"]


@pytest.mark.anyio
async def test_memory_restore_roundtrip(client):
    documents = [
        {"id": "game-1:0", "content": {"text": "Memory one."}, "metadata": {}}
    ]
    await client.post("/memory/upsert", json={"namespace": "game-1", "documents": documents})
    exported = (await client.get("/memory/export/game-1")).json()["chunks"]
    assert exported

    resp = await client.delete("/memory/clear", params={"namespace": "game-1"})
    assert resp.status_code == 200
    assert (await client.get("/memory/export/game-1")).json()["chunks"] == []

    resp = await client.post("/memory/restore", json={"namespace": "game-1", "chunks": exported})
    assert resp.status_code == 200
    assert resp.json()["restored"] == len(exported)
    assert (await client.get("/memory/export/game-1")).json()["chunks"] == exported


@pytest.mark.anyio
async def test_memory_clear(client):
    documents = [{"id": "game-1:0", "content": {"text": "Doomed."}, "metadata": {}}]
    await client.post("/memory/upsert", json={"namespace": "game-1", "documents": documents})
    resp = await client.delete("/memory/clear", params={"namespace": "game-1"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert (await client.get("/memory/export/game-1")).json()["chunks"] == []


@pytest.mark.anyio
async def test_rag_endpoints_removed(client):
    resp = await client.post("/rag/staging/push", json={"uuid": "u1", "text": "x"})
    assert resp.status_code == 404
    resp = await client.get("/rag/staging/count")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_output_cache_endpoints(client):
    data = {"uuid": "u1", "story": "A short tale.", "tool_results": []}
    resp = await client.put("/output/u1", json=data)
    assert resp.status_code == 200
    resp = await client.get("/output/u1")
    assert resp.status_code == 200
    assert resp.json() == data
    assert (await client.get("/output/count")).json() == {"count": 1}


@pytest.mark.anyio
async def test_queue_endpoints(client):
    resp = await client.post("/queue/push", params={"uuid": "u1", "data": json.dumps({"a": 1})})
    assert resp.status_code == 200
    resp = await client.get("/queue/length")
    assert resp.json() == {"length": 1}
    resp = await client.get("/queue/pop")
    assert resp.json()["item"]["a"] == 1


@pytest.mark.anyio
async def test_games_state_endpoints(client):
    resp = await client.put("/games/u1/state/hp", params={"value": "42"})
    assert resp.status_code == 200
    resp = await client.get("/games/u1/state/hp")
    assert resp.json() == 42
    resp = await client.delete("/games/u1/state/hp")
    assert resp.json() == {"ok": True}


@pytest.mark.anyio
async def test_game_state_404(client):
    resp = await client.get("/games/missing/state")
    assert resp.status_code == 404
