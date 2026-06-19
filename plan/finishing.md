# Finishing — Remaining Work

## rpg_ai_server (this project)

### DB 0 — Queue
- [ ] DLQ cleanup — `ZREMRANGEBYSCORE games:queue:dead -inf {now-7d}`
- [ ] Alert when dead letter queue > 100 items

### DB 1 — Game State
- [ ] `games:{uuid}:coord:{x}_{y}` → chunk index mapping for RAG (shared with Chroma worker)
- [ ] Field-level dirty tracking — only HSET fields that actually mutated (H9)
- [ ] `version` field on state Hash for future optimistic locking (M4)
- [ ] `status` field (`idle`/`processing`/`error`) on state Hash (M5)

### DB 2 — RAG Staging
- [ ] Content-hash check — `sha256(story)` before enqueue; skip if unchanged (H3)
- [ ] Include `chunk_ids` in drain payload (M3)

### Stale Data Cleanup
- [ ] Lua script: `SCAN 0 MATCH games:*:state` → `TTL` check → `DEL` stale keys + associated locks (C7)
- [ ] Cron or background loop every 5-10 min
- [ ] Also cleanup abandoned `rag:{uuid}:*` staging keys

### Response Path (Low Priority)
- [ ] `games:{uuid}:response` Hash + `PUBLISH games:{uuid}:notify` for web server (H4)

### Testing
- [ ] Unit tests for compression roundtrip
- [ ] Unit tests for `QueueManager` (backoff, delayed, dead)
- [ ] Unit tests for `GameStateManager` (load/save/drain)
- [ ] Integration test with mock Upstash Redis
- [ ] Integration test with mock Chroma worker

---

## chroma-worker (separate project)

### Worker Loop
- [ ] `async def chroma_worker_loop()` — infinite poll from `rag:queue`
- [ ] `LPOP rag:queue` → parse payload → decompress text

### Chunking & Embedding
- [ ] `estimate_tokens(text)` → `len(text) // 4`
- [ ] `split_into_chunks(text, max_tokens=10000)` — split on paragraph boundaries
- [ ] Generate embeddings with sentence-transformers (384-dim `all-MiniLM-L6-v2`)

### Chroma Storage
- [ ] Connect to Chroma DB (hosted or local)
- [ ] Collection naming: `game_memory_{uuid}`
- [ ] HNSW index configuration
- [ ] `collection.add(documents=chunks, ids=[...], metadatas=[...])`

### Cleanup
- [ ] `DEL rag:{uuid}:*` after successful Chroma ingestion
- [ ] Periodic cleanup of abandoned Chroma collections

### Integration Points
- [ ] `node4_tool_agent` — Chroma similarity search for RAG context
- [ ] Inject `PREVIOUS MEMORIES: {rag_context}` into LLM prompt
- [ ] Shared `split_into_chunks()` between AI server and Chroma worker (duplicate or package)

---

## Configuration

### .env for rpg_ai_server
```ini
UPSTASH_REDIS_RAG_URL=https://your-rag-instance.upstash.io
UPSTASH_REDIS_RAG_TOKEN=your-rag-token
```

### .env for chroma-worker
```ini
CHROMA_HOST=http://localhost:8000
UPSTASH_REDIS_RAG_URL=https://your-rag-instance.upstash.io
UPSTASH_REDIS_RAG_TOKEN=your-rag-token
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIM=384
CHUNK_MAX_TOKENS=10000
```

---

## Dependency Graph

```
rpg_ai_server                             chroma-worker
     │                                          │
     │  RPUSH rag:queue                          │  LPOP rag:queue
     ├──────────────────────────────────────────►│
     │  {"uuid","text","chunk_count"}            │  decompress → chunk → embed
     │                                          │  store in Chroma DB
     │                                          │  DEL rag:{uuid}:*
     │                                          │
     │  ┌─ coordinator mapping ──┐              │
     │  │ games:{uuid}:coord:{x} │ ←──── shared ──┤ split_into_chunks()
     │  └────────────────────────┘   function    │
     │                                          │
     │  queries Chroma for RAG context            │
     │◄──────────────────────────────────────────┤
     │  (direct, not through Redis)               │
```

Nothing is blocked — all remaining items are independent and can be done in any order.
