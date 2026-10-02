from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

_root = str(Path(__file__).resolve().parents[1])
if _root not in sys.path:
    sys.path.insert(0, _root)

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

try:
    import aiohttp
except ImportError:
    aiohttp = None

from rpg_ai_server.redis.client import InputRedisClient, GamesRedisClient, OutputRedisClient
from rpg_ai_server.redis.vector_memory import GameMemory

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


# ── Trigger (atomic drain per plan §5) ──

NEXTJS_WEBHOOK = os.getenv("NEXTJS_WEBHOOK_URL")


@app.post("/trigger")
async def trigger():
    c = await _get_input()
    g = await _get_games()
    o = await _get_output()
    raw = c.client

    # 1. Verify trigger:busy is set (Next.js locked before calling)
    busy = await raw.get("trigger:busy")
    if not busy:
        raise HTTPException(status_code=409, detail="not triggered")

    # 2. Atomic drain — RENAME to processing queue
    try:
        await raw.rename("input:queue", "input:queue:processing")
    except Exception:
        return {"ok": True, "items": 0}

    # 3. LPOP all items
    items = []
    failed = 0
    while True:
        raw_item = await raw.lpop("input:queue:processing")
        if raw_item is None:
            break
        try:
            items.append(json.loads(raw_item))
        except (json.JSONDecodeError, TypeError, ValueError):
            failed += 1
            continue

    # 4. Process each item
    processed = []
    for item in items:
        sid = item.get("uuid")
        if not sid:
            continue
        try:
            state = await g.hgetall(sid)
            if not state:
                continue
            output = {"sid": sid, "story": "(processed)", "tool_results": []}
            await o.push_result(sid, output)
            await g.expire(sid, 3600)
            if NEXTJS_WEBHOOK and aiohttp:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        NEXTJS_WEBHOOK,
                        json={"uuid": sid},
                        timeout=aiohttp.ClientTimeout(total=5),
                    )
            processed.append(sid)
        except Exception as e:
            processed.append(f"{sid}:error:{e}")

    # 5. Cleanup (only after attempting all items)
    await raw.delete("input:queue:processing")
    await raw.delete("trigger:busy")

    return {"ok": True, "items": len(processed), "processed": processed, "failed": failed}


# ── Health ──


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Queue (input:queue, input:queue:delayed, input:queue:dead) ──


@app.post("/queue/push")
async def queue_push(uuid: str = Query(...), data: str = Query(...)):
    c = await _get_input()
    try:
        parsed = json.loads(data)
    except (json.JSONDecodeError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Invalid JSON")
    await c.push_request(uuid, parsed)
    return {"ok": True, "uuid": uuid}


@app.get("/queue/pop")
async def queue_pop():
    c = await _get_input()
    item = await c.pop_request()
    if item is None:
        return {"ok": False, "item": None}
    return {"ok": True, "item": item}


@app.get("/queue/length")
async def queue_length():
    c = await _get_input()
    n = await c.queue_length()
    return {"length": n}


@app.post("/queue/delayed/push")
async def queue_delayed_push(item: dict, score: float = Query(...)):
    c = await _get_input()
    await c.push_delayed(item, score)
    return {"ok": True}


@app.get("/queue/delayed/pop")
async def queue_delayed_pop(max_score: float = Query(...)):
    c = await _get_input()
    items = await c.pop_delayed_due(max_score)
    return {"count": len(items), "items": items}


@app.post("/queue/dead/push")
async def queue_dead_push(item: dict):
    c = await _get_input()
    await c.push_dead(item)
    return {"ok": True}


# ── Game State (games:{uuid}:state) ──


@app.get("/games/{uuid}/state")
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


@app.get("/games/{uuid}/state/{field}")
async def game_state_get_field(uuid: str, field: str):
    c = await _get_games()
    value = await c.hget(uuid, field)
    if value is None:
        raise HTTPException(404, f"Field '{field}' not found")
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {"value": value}


@app.put("/games/{uuid}/state/{field}")
async def game_state_set_field(uuid: str, field: str, value: str = Query(...)):
    c = await _get_games()
    await c.hset(uuid, field, value)
    return {"ok": True}


@app.delete("/games/{uuid}/state/{field}")
async def game_state_del_field(uuid: str, field: str):
    c = await _get_games()
    ok = await c.hdel(uuid, field)
    return {"ok": ok}


@app.post("/games/{uuid}/counter/incr")
async def game_counter_incr(uuid: str):
    c = await _get_games()
    n = await c.incr(uuid)
    return {"counter": n}


@app.put("/games/{uuid}/counter")
async def game_counter_set(uuid: str, value: int = Query(...)):
    c = await _get_games()
    await c.set_counter(uuid, value)
    return {"ok": True}


@app.get("/games/{uuid}/lock")
async def game_lock_acquire(uuid: str, worker_id: str = Query(...), ttl: int = Query(default=30)):
    c = await _get_games()
    acquired = await c.acquire_lock(uuid, worker_id, ttl)
    return {"acquired": acquired}


@app.delete("/games/{uuid}/lock")
async def game_lock_release(uuid: str, worker_id: str = Query(...)):
    c = await _get_games()
    released = await c.release_lock(uuid, worker_id)
    return {"released": released}


@app.post("/games/{uuid}/expire")
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


@app.post("/memory/query")
async def memory_query(req: MemoryQueryRequest):
    hits = await _get_memory().query(req.namespace, req.query, top_k=req.top_k)
    return {"hits": hits}


@app.post("/memory/upsert")
async def memory_upsert(req: MemoryUpsertRequest):
    count = await _get_memory().upsert(req.namespace, req.documents)
    return {"ok": True, "chunks": count}


@app.get("/memory/export/{sid}")
async def memory_export(sid: str):
    chunks = await _get_memory().export(sid)
    return {
        "sid": sid,
        "saved_at": int(time.time() * 1000),
        "next_cursor": None,
        "chunks": chunks,
    }


@app.post("/memory/restore")
async def memory_restore(req: MemoryRestoreRequest):
    count = await _get_memory().restore(req.namespace, req.chunks)
    return {"ok": True, "restored": count}


@app.delete("/memory/clear")
async def memory_clear(namespace: str = Query(...)):
    await _get_memory().clear(namespace)
    return {"ok": True}


# ── Output Cache (output:{uuid}) ──


@app.get("/output/count")
async def output_count():
    c = await _get_output()
    n = await c.count()
    return {"count": n}


@app.get("/output/{uuid}")
async def output_get(uuid: str):
    c = await _get_output()
    data = await c.get_json(uuid)
    if data is None:
        raise HTTPException(404, "Output not found")
    return data


@app.put("/output/{uuid}")
async def output_set(uuid: str, data: dict):
    c = await _get_output()
    await c.push_result(uuid, data)
    return {"ok": True}


# ── General ──


@app.get("/keys")
async def get_keys(pattern: str = Query(default="*"), prefix: str = Query(default="")):
    prefix_map = {"input": _input, "games": _games, "output": _output}
    c = prefix_map.get(prefix)
    if c is None:
        cl = await _get_input()
        return await cl.keys(pattern)
    return await c.keys(pattern)


@app.get("/dbsize")
async def dbsize(prefix: str = Query(default="")):
    prefix_map = {"input": _input, "games": _games, "output": _output}
    c = prefix_map.get(prefix)
    if c is None:
        all_keys = []
        for getter in (_get_input, _get_games, _get_output):
            cl = await getter()
            ks = await cl.keys("*")
            all_keys.extend(ks)
        return {"dbsize": len(all_keys)}
    return {"dbsize": await c.dbsize()}


@app.delete("/keys/{key:path}")
async def delete_key(key: str, prefix: str = Query(default="")):
    prefix_map = {"input": _input, "games": _games, "output": _output}
    c = prefix_map.get(prefix)
    if c is None:
        raise HTTPException(400, "prefix required (input/games/output)")
    ok = await c.delete(key)
    return {"ok": ok}
