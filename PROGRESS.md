# Progress — D&D RPG AI System

Two repos: AI server `D:\AI agent` (Python FastAPI + LangGraph), web app `D:\deepslate dungeons` (Next.js).

## Done + verified

### 1. Game memory → Upstash Search (replaces old Vector/embedding plan)
- `rpg_ai_server/config/settings.py`: `SearchConfig` (UPSTASH_SEARCH_REST_URL/TOKEN, index `game-memory`, top_k 3). `VectorConfig` removed.
- `rpg_ai_server/redis/vector_memory.py`: `GameMemory` rewritten on the `upstash-search` SDK — no client embeddings (Upstash embeds server-side). One shared index; games scoped by `sid` (in content + metadata, id prefix `{sid}:`). `query` uses filter `@metadata.sid = '<sid>'`; `export` = `fetch(prefix=...)`; `clear` = `delete(filter=...)`; chunker (512/32 tokens) kept; `upsert_chunks(uuid, texts, turn, is_incident)` signature unchanged.
- `rpg_ai_server/redis_api.py`: `/memory/query {namespace, query, top_k}` / `upsert {namespace, documents}` / `export/{sid}` / `restore` / `clear?namespace=`.
- `requirements.txt`: `upstash-search` in; `upstash-vector`, `sentence-transformers` out.
- Live verified on the real Search DB (`polished-turtle-43316-gcp-usc1-search.upstash.io`): upsert → ranked query (0.88 relevance) → export → restore → clear.

### 2. Infra: Upstash Redis unblocked + full live E2E
- New Redis `https://handy-longhorn-80079.upstash.io` wired in `rpg_ai_server\.env` (older hosts `dynamic-stag-74768`, `rational-falcon-116542`, `discussion-intense-...redis.io` are dead).
- Live smoke passed: health, queue push/len/pop, games state hash set/get, counter, lock acquire/reject/release, output put/count/get, memory roundtrip, cleanup. (`/keys`/`/dbsize` blocked by Upstash — expected.)

### 3. Lock bug (found by the live E2E)
- `upstash_redis` SDK returns `False` (not `None`) when `SET NX` fails → `acquire_lock` misreported. Fixed `return bool(result)` in `redis/client.py` (line ~229). Regression tests in `tests/test_lock_client.py`.

### 4. Web scenario play flow (built from scratch — `lib/scenarios.ts` was orphaned)
- `app/api/ai-server/[...path]/route.ts`: CORS-free relay to the AI server (default `http://127.0.0.1:8000`, `AI_SERVER_URL`).
- `lib/playClient.ts`: typed client (queuePush, outputGet, counterIncr, stateSetField, memoryExport/Restore/Clear).
- `components/game/ScenarioEntry.tsx`: registry — resume / restore / delete / create.
- `components/game/PlayScreen.tsx`: chat UI — queue push → poll `output/{sid}` (2s, ~2min budget, dedupe via last-consumed story) → turn counter → autosave/10 turns → exit modal (Save / Don't save = wipe / Keep playing). Restores blob into the Search index on entry. Persists `rpg:turn:{sid}`, `rpg:ready:{sid}`.
- `components/game/PlayGate.tsx`, `app/play/page.tsx`, `app/play/[sid]/page.tsx`.
- `types/ai-server.ts`: `AiMemoryChunk {id, content, metadata}`, `AiMemoryHit {…, score}`.
- `tsc --noEmit` and `npm run build` clean. Routes: `/api/ai-server/[...path]`, `/api/games/[id]/memory`, `/play`, `/play/[sid]`.

### 5. RAG read path (was missing — only the drain/write path existed)
- `schemas/state.py`: new `rag_context: str`; `engine/orchestrator.py` initializes `""`.
- `agents/node4_tool_agent/agent.py`: `_retrieve_memories()` queries Upstash Search (sid + current prompt), injects `[memory N | turn X | relevance Y]` blocks into the tool-agent prompt, returns `rag_context`; failure-proof (returns `""` if unconfigured/errors).
- Live smoke: seed → retrieve (0.88 vs 0.00) → cleanup, OK.

### 6. Tests + docs
- `tests/fakes.py`: `FakeSearchIndex`/`FakeSearchDoc` replaced vector fakes.
- `tests/test_search_memory.py` (renamed from test_vector_memory), `test_game_state.py`, `test_redis_api.py` re-shaped; `test_lock_client.py` added. **82 tests pass.**
- `REDIS_API.md` + `README.md` updated to the Upstash Search contract.

## Pending
- **Live full-pipeline LLM run** (only item): start `python -m rpg_ai_server.main` (engine), push a real turn (`POST /queue/push`), poll `output/{sid}` for the generated story (node4/node5/node6 LLM calls), confirm memory drain, clean up.
- Optional later: surface `rag_context` in node5/node6 narrative; web panel showing retrieved memories via `aiServer.memory.query`.

## Boot commands
- Engine: `python -m rpg_ai_server.main` (from `D:\AI agent`)
- API-only: `python -m uvicorn rpg_ai_server.redis_api:app --port 8055`
- Web: `npm run dev` (from `D:\deepslate dungeons`) → `/play`