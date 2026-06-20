from __future__ import annotations

import json
import sys
from pathlib import Path

_src = str(Path(__file__).resolve().parent)
if _src not in sys.path:
    sys.path.insert(0, _src)

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from redis.client import InputRedisClient, GamesRedisClient, RagRedisClient, OutputRedisClient

app = FastAPI(title="RPG AI Redis API")

_input: InputRedisClient | None = None
_games: GamesRedisClient | None = None
_rag: RagRedisClient | None = None
_output: OutputRedisClient | None = None


async def _get_input() -> InputRedisClient:
    global _input
    if _input is None:
        _input = InputRedisClient()
        await _input.connect()
    return _input


async def _get_games() -> GamesRedisClient:
    global _games
    if _games is None:
        _games = GamesRedisClient()
        await _games.connect()
    return _games


async def _get_rag() -> RagRedisClient:
    global _rag
    if _rag is None:
        _rag = RagRedisClient()
        await _rag.connect()
    return _rag


async def _get_output() -> OutputRedisClient:
    global _output
    if _output is None:
        _output = OutputRedisClient()
        await _output.connect()
    return _output


# ── Startup / Shutdown ──


@app.on_event("startup")
async def startup():
    await _get_input()
    await _get_games()
    await _get_rag()
    await _get_output()


@app.on_event("shutdown")
async def shutdown():
    for c in [_input, _games, _rag, _output]:
        if c:
            await c.disconnect()


# ── Health ──


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Queue (input:queue, input:queue:delayed, input:queue:dead) ──


@app.post("/queue/push")
async def queue_push(uuid: str = Query(...), data: str = Query(...)):
    c = await _get_input()
    parsed = json.loads(data)
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
    if raw is None:
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


# ── RAG Staging (rag:queue) ──


@app.post("/rag/staging/push")
async def rag_staging_push(payload: dict):
    c = await _get_rag()
    await c.push_staging(payload)
    return {"ok": True}


@app.get("/rag/staging/pop")
async def rag_staging_pop():
    c = await _get_rag()
    item = await c.pop_staging()
    if item is None:
        return {"ok": False, "item": None}
    return {"ok": True, "item": item}


@app.get("/rag/staging/count")
async def rag_staging_count():
    c = await _get_rag()
    n = await c.staging_count()
    return {"count": n}


@app.get("/rag/chunk/{uuid}/{index}")
async def rag_chunk_get(uuid: str, index: int):
    c = await _get_rag()
    chunk = await c.get_chunk(uuid, index)
    if chunk is None:
        raise HTTPException(404, "Chunk not found")
    return chunk


# ── Output Cache (output:{uuid}) ──


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


@app.get("/output/count")
async def output_count():
    c = await _get_output()
    n = await c.count()
    return {"count": n}


# ── General ──


@app.get("/keys")
async def get_keys(pattern: str = Query(default="*"), prefix: str = Query(default="")):
    prefix_map = {"input": _input, "games": _games, "rag": _rag, "output": _output}
    c = prefix_map.get(prefix)
    if c is None:
        cl = await _get_input()
        return await cl.keys(pattern)
    return await c.keys(pattern)


@app.get("/dbsize")
async def dbsize(prefix: str = Query(default="")):
    prefix_map = {"input": _input, "games": _games, "rag": _rag, "output": _output}
    c = prefix_map.get(prefix)
    if c is None:
        all_keys = []
        for p, client in prefix_map.items():
            cl = await client
            ks = await cl.keys("*")
            all_keys.extend(ks)
        return {"dbsize": len(all_keys)}
    return {"dbsize": await c.dbsize()}


@app.delete("/keys/{key:path}")
async def delete_key(key: str, prefix: str = Query(default="")):
    prefix_map = {"input": _input, "games": _games, "rag": _rag, "output": _output}
    c = prefix_map.get(prefix)
    if c is None:
        raise HTTPException(400, "prefix required (input/games/rag/output)")
    ok = await c.delete(key)
    return {"ok": ok}
