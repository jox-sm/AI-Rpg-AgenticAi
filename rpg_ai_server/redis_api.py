from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

_root = str(Path(__file__).resolve().parents[1])
if _root not in sys.path:
    sys.path.insert(0, _root)

from fastapi import APIRouter, FastAPI, HTTPException, Query
from pydantic import BaseModel

from rpg_ai_server.redis.client import InputRedisClient, GamesRedisClient, OutputRedisClient
from rpg_ai_server.redis.vector_memory import GameMemory

# Routes live on a router so the gameplay API can be mounted by more than one
# app: `redis_api:app` (API only, tests) and `api:app` (API + in-process engine).
router = APIRouter()

app = FastAPI(title="RPG AI Redis API")

_input: InputRedisClient | None = None
_games: GamesRedisClient | None = None
_output: OutputRedisClient | None = None
_memory: GameMemory | None = None

# Guards lazy singletons: two concurrent first-requests must not both connect.
_connect_lock: asyncio.Lock | None = None


def _lock() -> asyncio.Lock:
    global _connect_lock
    if _connect_lock is None:
        _connect_lock = asyncio.Lock()
    return _connect_lock


async def _get_input() -> InputRedisClient:
    global _input
    if _input is None:
        async with _lock():
            if _input is None:
                _input = InputRedisClient()
                await _input.connect()
    return _input


async def _get_games() -> GamesRedisClient:
    global _games
    if _games is None:
        async with _lock():
            if _games is None:
                _games = GamesRedisClient()
                await _games.connect()
    return _games


async def _get_output() -> OutputRedisClient:
    global _output
    if _output is None:
        async with _lock():
            if _output is None:
                _output = OutputRedisClient()
                await _output.connect()
    return _output


def _get_memory() -> GameMemory:
    global _memory
    if _memory is None:
        _memory = GameMemory()
    return _memory


def _memory_or_503() -> GameMemory:
    """Memory endpoints degrade gracefully when Upstash Search is not configured.

    Gameplay (queue/state/output) runs fine without Search creds — the engine
    skips memory enrichment — but memory/query|upsert|export|restore|clear need
    them. Return a clear 503 instead of an opaque 500.
    """
    from rpg_ai_server.config.settings import settings

    if not settings.search.configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "Game memory is not configured: set UPSTASH_SEARCH_REST_URL and "
                "UPSTASH_SEARCH_REST_TOKEN in rpg_ai_server/.env (Upstash console "
                "→ Search → create index). Gameplay works without it; the "
                "memory/saves features are disabled until then."
            ),
        )
    return _get_memory()


# ── Startup / Shutdown ──


@app.on_event("startup")
async def startup():
    await _get_input()
    await _get_games()
    await _get_output()


@app.on_event("shutdown")
async def shutdown():
    for c in [_input, _games, _output]:
        if c:
            await c.disconnect()


# ── Trigger (advisory only — the engine consumes input:queue itself) ──
# MultiTaskEngine.run polls input:queue continuously (~100ms idle cadence), so
# pushes do NOT need a trigger to be processed. Calling this endpoint never
# drains or consumes anything: any consumer racing the engine would steal real
# player turns. Kept for back-compat as a push-landed status probe.


@router.post("/trigger")
async def trigger():
    c = await _get_input()
    queued = await c.queue_length()
    # Dead letter is a ZSET in the current implementation (queue:dead), but
    # tolerate other shapes from older runs instead of 500-ing the probe.
    try:
        dead = await c.client.zcard("input:queue:dead")
    except Exception:
        try:
            dead = await c.client.llen("input:queue:dead")
        except Exception:
            dead = None
    return {
        "ok": True,
        "queued": queued,
        "dead_lettered": dead,
        "note": "engine polls input:queue directly; no items consumed here",
    }


# ── Health ──


@router.get("/health")
async def health():
    return {"status": "ok"}


# ── Queue (input:queue, input:queue:delayed, input:queue:dead) ──


@router.post("/queue/push")
async def queue_push(uuid: str = Query(...), data: str = Query(...)):
    c = await _get_input()
    try:
        parsed = json.loads(data)
    except (json.JSONDecodeError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Invalid JSON")
    await c.push_request(uuid, parsed)
    return {"ok": True, "uuid": uuid}


@router.get("/queue/pop")
async def queue_pop():
    c = await _get_input()
    item = await c.pop_request()
    if item is None:
        return {"ok": False, "item": None}
    return {"ok": True, "item": item}


@router.get("/queue/length")
async def queue_length():
    c = await _get_input()
    n = await c.queue_length()
    return {"length": n}


@router.post("/queue/delayed/push")
async def queue_delayed_push(item: dict, score: float = Query(...)):
    c = await _get_input()
    await c.push_delayed(item, score)
    return {"ok": True}


@router.get("/queue/delayed/pop")
async def queue_delayed_pop(max_score: float = Query(...)):
    c = await _get_input()
    items = await c.pop_delayed_due(max_score)
    return {"count": len(items), "items": items}


@router.post("/queue/dead/push")
async def queue_dead_push(item: dict):
    c = await _get_input()
    await c.push_dead(item)
    return {"ok": True}


# ── Game State (games:{uuid}:state) ──


@router.get("/games/{uuid}/state")
async def game_state_get(uuid: str):
    c = await _get_games()
    raw = await c.hgetall(uuid)
    if not raw:
        raise HTTPException(404, "Game not found")
    decoded = {}
    for field, value in raw.items():
        try:
            decoded[field] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            decoded[field] = value
    return decoded


@router.get("/games/{uuid}/state/{field}")
async def game_state_get_field(uuid: str, field: str):
    c = await _get_games()
    value = await c.hget(uuid, field)
    if value is None:
        raise HTTPException(404, f"Field '{field}' not found")
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {"value": value}


@router.put("/games/{uuid}/state/{field}")
async def game_state_set_field(uuid: str, field: str, value: str = Query(...)):
    c = await _get_games()
    await c.hset(uuid, field, value)
    return {"ok": True}


@router.delete("/games/{uuid}/state/{field}")
async def game_state_del_field(uuid: str, field: str):
    c = await _get_games()
    ok = await c.hdel(uuid, field)
    return {"ok": ok}


@router.post("/games/{uuid}/counter/incr")
async def game_counter_incr(uuid: str):
    c = await _get_games()
    n = await c.incr(uuid)
    return {"counter": n}


@router.put("/games/{uuid}/counter")
async def game_counter_set(uuid: str, value: int = Query(...)):
    c = await _get_games()
    await c.set_counter(uuid, value)
    return {"ok": True}


@router.get("/games/{uuid}/lock")
async def game_lock_acquire(uuid: str, worker_id: str = Query(...), ttl: int = Query(default=30)):
    c = await _get_games()
    acquired = await c.acquire_lock(uuid, worker_id, ttl)
    return {"acquired": acquired}


@router.delete("/games/{uuid}/lock")
async def game_lock_release(uuid: str, worker_id: str = Query(...)):
    c = await _get_games()
    released = await c.release_lock(uuid, worker_id)
    return {"released": released}


@router.post("/games/{uuid}/expire")
async def game_expire(uuid: str, ttl: int = Query(...)):
    c = await _get_games()
    ok = await c.expire(uuid, ttl)
    return {"ok": ok}


# ── Game Memory (Upstash Search, shared index filtered by sid) ──
# Contract: the client sends plain text (see AiMemoryChunk in the web app) —
# chunking happens server-side during drain (GameStateManager); search is
# AI-hybrid (semantic + full-text) so the client never sends embeddings.


class MemoryQueryRequest(BaseModel):
    namespace: str
    query: str
    top_k: int = 5


class MemoryUpsertRequest(BaseModel):
    namespace: str
    documents: list[dict]


class MemoryRestoreRequest(BaseModel):
    namespace: str
    chunks: list[dict]


@router.post("/memory/query")
async def memory_query(req: MemoryQueryRequest):
    hits = await _memory_or_503().query(req.namespace, req.query, top_k=req.top_k)
    return {"hits": hits}


@router.post("/memory/upsert")
async def memory_upsert(req: MemoryUpsertRequest):
    count = await _memory_or_503().upsert(req.namespace, req.documents)
    return {"ok": True, "chunks": count}


@router.get("/memory/export/{sid}")
async def memory_export(sid: str):
    chunks = await _memory_or_503().export(sid)
    return {
        "sid": sid,
        "saved_at": int(time.time() * 1000),
        "next_cursor": None,
        "chunks": chunks,
    }


@router.post("/memory/restore")
async def memory_restore(req: MemoryRestoreRequest):
    count = await _memory_or_503().restore(req.namespace, req.chunks)
    return {"ok": True, "restored": count}


@router.delete("/memory/clear")
async def memory_clear(namespace: str = Query(...)):
    await _memory_or_503().clear(namespace)
    return {"ok": True}


# ── Output Cache (output:{uuid}) ──


@router.get("/output/count")
async def output_count():
    c = await _get_output()
    n = await c.count()
    return {"count": n}


@router.get("/output/{uuid}")
async def output_get(uuid: str):
    c = await _get_output()
    data = await c.get_json(uuid)
    if data is None:
        raise HTTPException(404, "Output not found")
    return data


@router.put("/output/{uuid}")
async def output_set(uuid: str, data: dict):
    c = await _get_output()
    await c.push_result(uuid, data)
    return {"ok": True}


# ── General ──


@router.get("/keys")
async def get_keys(pattern: str = Query(default="*"), prefix: str = Query(default="")):
    getters = {"input": _get_input, "games": _get_games, "output": _get_output}
    getter = getters.get(prefix)
    if getter is None:
        cl = await _get_input()
        return await cl.keys(pattern)
    return await (await getter()).keys(pattern)


@router.get("/dbsize")
async def dbsize(prefix: str = Query(default="")):
    getters = {"input": _get_input, "games": _get_games, "output": _get_output}
    getter = getters.get(prefix)
    if getter is None:
        all_keys = []
        for g in (_get_input, _get_games, _get_output):
            cl = await g()
            ks = await cl.keys("*")
            all_keys.extend(ks)
        return {"dbsize": len(all_keys)}
    return {"dbsize": await (await getter()).dbsize()}


@router.delete("/keys/{key:path}")
async def delete_key(key: str, prefix: str = Query(default="")):
    getters = {"input": _get_input, "games": _get_games, "output": _get_output}
    getter = getters.get(prefix)
    if getter is None:
        raise HTTPException(400, "prefix required (input/games/output)")
    c = await getter()
    ok = await c.delete(key)
    return {"ok": ok}


# All gameplay routes live on `router`; `app` mounts them (this include runs at
# module import — `api.py` reuses the same `app` instance rather than building
# a second app so the router is only ever included once).
app.include_router(router)
