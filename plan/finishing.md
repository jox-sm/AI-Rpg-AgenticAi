# Finishing — Remaining Work

## rpg_ai_server (this project)

### DB 0 — Queue
- [ ] DLQ cleanup — `ZREMRANGEBYSCORE games:queue:dead -inf {now-7d}`
- [ ] Alert when dead letter queue > 100 items

### DB 1 — Game State
- [ ] Field-level dirty tracking — only HSET fields that actually mutated (H9)
- [ ] `version` field on state Hash for future optimistic locking (M4)
- [ ] `status` field (`idle`/`processing`/`error`) on state Hash (M5)

### Remove RAG/DB 2 leftovers
- [ ] Delete `redis/rag_cache.py` (RagCache wrapper)
- [ ] Remove `RagRedisClient` + `rag_db` / `UPSTASH_REDIS_RAG_*` from `main.py`, `config/settings.py`, `.env.example`, `redis_api.py` (rag endpoints)
- [ ] Remove `requirements.txt` entries for the old RAG stack (chromadb etc. if present)

### Game Memory (Upstash Vector)
- [ ] Add `upstash-vector` + `sentence-transformers` to `requirements.txt`
- [ ] Add `UPSTASH_VECTOR_REST_URL` / `UPSTASH_VECTOR_REST_TOKEN` (+ model/dim/top_k) to `.env.example` and `settings.py`
- [ ] `split_into_chunks()` — 10k-token chunks on paragraph boundaries, `estimate_tokens() = len(text) // 4`
- [ ] Embedding model loaded once at boot (`all-MiniLM-L6-v2`, 384-dim)
- [ ] Drain → split → embed → `index.upsert(..., namespace=uuid)` (in `try_drain()`)
- [ ] Content-hash check — `sha256(story + incidents)`; skip upsert if unchanged (H3)
- [ ] `node4_tool_agent` — query top_k=5, inject `PREVIOUS MEMORIES: {rag_context}` into prompt
- [ ] Namespace cleanup on `game_over` + in stale-data sweep (`index.delete(namespace=uuid)`)

### Scenario Lifecycle (named save slots)
- [ ] `GET /memory/export/{sid}` — full namespace dump via `index.range(include_vectors=True, include_metadata=True)` (rpg_ai_server)
- [ ] `POST /memory/restore` — upsert saved chunks back into a namespace (no re-embedding — vectors shipped in the blob)
- [ ] Namespace cleanup on `game_over` / "Don't save" exit — never on regular exit (rpg_ai_server)

> Frontend work (Next.js routes, scenario registry, exit popup, autosave-every-10) is **not tracked here** — the fullstack app has its own folder.

### Stale Data Cleanup
- [ ] Lua script: `SCAN 0 MATCH games:*:state` → `TTL` check → `DEL` stale keys + associated locks (C7)
- [ ] Cron or background loop every 5-10 min
- [ ] Same sweep also deletes expired session namespaces in Upstash Vector

### Response Path (Low Priority)
- [ ] `games:{uuid}:response` Hash + `PUBLISH games:{uuid}:notify` for web server (H4)

### Loop Guards (see `plan/loops.md`)
- [ ] `conditional_passes` in state schema; router cap (4 passes, clear flags + fall through) in `router_node` (L1, L2)
- [ ] `RemainingSteps` degradation in `route_from_conditional` (≤10 steps → route to node4) (L2)
- [ ] `ainvoke(..., config={"recursion_limit": 60})` + `except GraphRecursionError` → graceful story output (L4)
- [ ] `ToolCallLimitMiddleware(max_total_tool_calls=15)` in node4 `create_agent` (L5)
- [ ] Futile-action guard — last-6 tool signatures, 3 repeats → stop (L6)
- [ ] 120s wall-clock timeout around `process_request` → partial + `error: timeout` (L7)
- [ ] node6 output validity assertions: non-empty story + state deltas (L8)
- [ ] LangSmith tracing env vars (L9); flow test: `graph.stream(stream_mode="updates")` in dev
- [ ] Test: router flip-flop simulation completes ≤4 passes (L10)

### Testing
- [ ] Unit tests for compression roundtrip
- [ ] Unit tests for `QueueManager` (backoff, delayed, dead)
- [ ] Unit tests for loop guards: router cap, futile-action guard, recursion-limit fallback (L10)
- [ ] Unit tests for `GameStateManager` (load/save/drain)
- [ ] Integration test with mock Upstash Redis
- [ ] Integration test for memory: upsert to a test Vector namespace → query → assert hits
- [ ] Integration test for export roundtrip: upsert → `range()` dump → restore into fresh namespace → query → same hits (server side)

---

## Memory pipeline (in-process, no separate worker)

Everything runs inside the AI server — no `chroma-worker` project anymore.

```
drain → decompress(gzip) → split_into_chunks() → embed (384-dim) →
       index.upsert(namespace={uuid})            query per turn (top_k=5)
```

- [ ] Shared helpers live in `rpg_ai_server/utils` (e.g., `utils/memory.py`)

---

## Configuration

### .env for rpg_ai_server
```ini
UPSTASH_VECTOR_REST_URL=https://your-vector-index.upstash.io
UPSTASH_VECTOR_REST_TOKEN=your-vector-token
VECTOR_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_EMBEDDING_DIM=384
VECTOR_TOP_K=5
VECTOR_CHUNK_MAX_TOKENS=10000
```

---

## Dependency Graph

```
rpg_ai_server
     │
     │  drain (10 actions OR major event)
     │    → decompress story/incidents (gzip)
     │    → split_into_chunks()          (utils/memory.py)
     │    → embed (all-MiniLM-L6-v2)
     │    → upsert ──────────────────────►  Upstash Vector
     │                                        namespace = {uuid}
     │
     │  per turn:
     │    → embed context query
     │    → index.query(top_k=5) ◄──────────  Upstash Vector
     │    → inject rag_context into LLM prompt
```

Nothing is blocked — all remaining items are independent and can be done in any order.