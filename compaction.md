# COMPACTION — Full Work Record: D&D RPG AI System

Generated: 2026-08-14 (session mega-summary). Source of truth for everything done, decided, tested, and pending.
Repos: AI server `D:\AI agent` (Python FastAPI + LangGraph), web app `D:\deepslate dungeons` (Next.js 16 / TypeScript).

---

## 0. Credentials & Env (live)

> SUPERSEDED 2026-10-03: credentials rotate; never store live secrets in docs.
> Current live hosts/keys live ONLY in gitignored `rpg_ai_server/.env`.
> - Upstash Search: configured in `.env` (`UPSTASH_SEARCH_REST_URL/TOKEN`, index `game-memory`). Old host `polished-turtle-43316...` retired.
> - Upstash Redis: configured in `.env` (`UPSTASH_REDIS_REST_URL/TOKEN`). Old host `handy-longhorn-80079` and all DNS-dead hosts (`dynamic-stag-74768`, `rational-falcon-116542`, `discussion-intense-...`) retired.
> - LLM: `OPENROUTER_API_KEY` in `.env` (OpenRouter-only; Gemini path removed).
> - Model map (live-verified 2026-10-03): classifier `liquid/lfm-2.5-2.6b:free`, image `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`, redescription `google/gemma-4-26b-a4b-it:free`, tool/story `qwen/qwen3.8-27b:free`, context `google/gemma-4-31b-it:free`. Dead: `owl-alpha`, `qwen3-coder:free`, `llama-3.2-3b:free`, `gemini-2.0-flash`.
> - Loop guards (generous local): `LOOP_RECURSION_LIMIT=60`, `ROUTER_MAX_PASSES=3`, `MAX_TOOL_CALLS=15`, `REQUEST_TIMEOUT_SECONDS=60.0`, `MAX_LLM_CALLS_PER_TURN=12`, `CONTEXT_MAX_CHARS=8000`, `CHAT_LOG_MAX_TURNS=40`, `DRAIN_THRESHOLD=25`, `MAX_CONCURRENT_REQUESTS=16`.

---

## 1. Task: Game Memory → Upstash Search (replaces Upstash Vector / sentence-transformers plan)

### Why
- User supplied real Upstash Search DB and explicitly preferred it ("not normal RAG db, it's much better").
- Upstash Search = AI-powered hybrid search (semantic 75% + full-text 25% default, configurable `semantic_weight`; server-side embeddings; optional AI reranking; input enrichment).
- Upstash Vector would need client-side embeddings (sentence-transformers 384-dim had to be installed/dumped). Removed entirely.

### SDK facts (installed: `upstash-search 0.1.1`, Python 3.14)
- `Search(url, token, *, retries=3, retry_interval=1.0, allow_telemetry=True)`; `Search.from_env()` reads `UPSTASH_SEARCH_REST_URL`/`UPSTASH_SEARCH_REST_TOKEN`.
- `Search.index(name) -> Index`
- `Index.upsert(documents: Document | dict | list)` — returns None
- `Index.search(query, *, limit=10, filter='', reranking=False, semantic_weight=0.75, input_enrichment=True) -> List[DocumentScore]`
- `Index.delete(*, ids=None, prefix=None, filter=None) -> int`
- `Index.fetch(*, ids=None, prefix=None) -> List[Document | None]`
- `Document{id:str, content:dict, metadata:dict|None}`; `DocumentScore` = Document + `score:float`
- NO `range()` / cursor API in Search SDK → export uses `fetch(prefix="{sid}:")`
- Content fields are searchable; metadata fields NOT searchable but filterable with `@metadata.` prefix
- Filter syntax: SQL-like; strings `'...'` or `"..."`; bools `1/0`; operators `=`, `!=`, `<`, `<=`, `>`, `>=`, `GLOB`, `NOT GLOB`, `IN`, `CONTAINS`, `HAS FIELD` (+ NOT variants); boolean `AND`/`OR`, parens; AND binds tighter
- Example: `@metadata.sid = 'game-1' AND @metadata.is_incident = 1`
- IMPORTANT: `upstash_redis` SDK `SET` with `nx=True` returns `False` (not `None`) when the key exists.

### File changes
1. `rpg_ai_server/config/settings.py`
   - Removed `VectorConfig` (upstash_vector_url/token, embedding_model, dimension 384, top_k, chunk 512/32, embedding_batch 64 + input_url/output_url/_auth_part properties — those three properties BELONG TO RedisConfig in the original file; earlier edit had accidentally nested them; final cleanup removed the whole stray block; RedisConfig no longer exposes input_url/output_url — nothing referenced them).
   - Added `SearchConfig`: `upstash_search_url`, `upstash_search_token` (env `UPSTASH_SEARCH_REST_URL/TOKEN`), `index_name` (`SEARCH_INDEX_NAME`, default `game-memory`), `top_k` (`SEARCH_TOP_K`, 3), `reranking` (`SEARCH_RERANKING`, false), `semantic_weight` (`SEARCH_SEMANTIC_WEIGHT`, 0.75), `input_enrichment` (`SEARCH_INPUT_ENRICHMENT`, true→ parse "true" default; `!= "false"`), `chunk_max_tokens` (512), `chunk_overlap_tokens` (32), `configured` property.
   - `Settings` now: `redis`, `models`, `app`, `search`.
   - `.env` loading: `load_dotenv(Path(__file__).resolve().parents[1] / ".env")` (package-relative).
2. `rpg_ai_server/redis/vector_memory.py` — FULL REWRITE (kept filename for import stability)
   - Kept: `estimate_tokens(text) = max(1, len//4)`, `split_into_chunks(text, max_tokens=None, overlap_tokens=None)` (sentence/line split on `(?<=[.!?])\s+|\n+`, tail-overlap flush, hard-split words > budget, char-level split for single oversized words via `chars_per_chunk = max_tokens*4-1`).
   - Removed: `Embedder` protocol, `SentenceTransformerEmbedder`, asyncio.Lock threading, namespace concept.
   - New `GameMemory(index=None)`:
     - `_connect()`: lazy; requires `settings.search.configured` else RuntimeError "UPSTASH_SEARCH_REST_URL / UPSTASH_SEARCH_REST_TOKEN not configured"; builds `Search(url, token).index(index_name)` once; logs "Connected to Upstash Search index 'game-memory'".
     - `_run(fn)`: `asyncio.to_thread(fn, index)` under `_thread_lock` (SDK is sync HTTP).
     - `upsert_chunks(namespace, texts, turn=0, is_incident=False) -> int`: doc id `f"{namespace}:{turn}:{i}:{uuid4().hex[:8]}"`, content `{"sid": ns, "text": text[:4000]}`, metadata `{sid, turn, index, is_incident(bool), ts(int)}`; calls `upsert`.
     - `upsert(namespace, documents) -> int`: prepares each `{id?, content(dict|str), metadata?}`; str content wrapped `{"sid", "text"[:4000]}`; dict gets `sid` defaulted; root-level `text` shortcut accepted; invalid docs (no content and no text) skipped; `metadata["sid"] = namespace` always stamped; missing id → `f"{namespace}:{uuid4().hex[:12]}"`.
     - `query(namespace, query_text, top_k=None) -> List[{id, score, content, metadata}]` via `index.search(query=..., limit=top_k or settings.search.top_k, filter=f"@metadata.sid = '{namespace}'", reranking=..., semantic_weight=..., input_enrichment=...)`; empty query → `[]`.
     - `export(namespace) -> List[{id, content, metadata}]` via `index.fetch(prefix=f"{namespace}:")` (per-game docs only, since ids are prefixed).
     - `restore(namespace, chunks) -> int` = `upsert(namespace, chunks)` (plain text, re-embedded server-side on upsert).
     - `clear(namespace) -> bool` via `index.delete(filter=f"@metadata.sid = '{namespace}'")`.
3. `rpg_ai_server/redis_api.py` — `/memory/*` re-shape:
   - Removed `MemoryQueryRequest{namespace, vector, top_k}` → `MemoryQueryRequest{namespace, query, top_k=5}`; removed `MemoryUpsertRequest.vectors` → `documents: list[dict]`; `MemoryRestoreRequest{namespace, chunks}` unchanged.
   - `POST /memory/query` → `_get_memory().query(namespace, query, top_k)` returns `{"hits": [...]}`
   - `POST /memory/upsert` → `_get_memory().upsert(namespace, documents)` returns `{"ok", "chunks"}`
   - `GET /memory/export/{sid}` → `{sid, saved_at(ms), next_cursor: None, chunks}`
   - `POST /memory/restore` → `{"ok", "restored"}`
   - `DELETE /memory/clear?namespace=` → `{"ok": True}`
   - Full HTTP surface (all live-verified): `/health GET`; `/trigger POST` (busy-key gated, RENAME drain, webhook optional); `/queue/push?uuid&data` POST (data = JSON string!), `/queue/pop` GET, `/queue/length` GET, `/queue/delayed/push?score` POST `{item dict}` (body = raw dict), `/queue/delayed/pop?max_score` GET, `/queue/dead/push` POST `{item}`; games: `/games/{uuid}/state` GET (decodes JSON fields), `/state/{field}` GET (JSON or `{value}`), PUT `?value=` (raw string!), DELETE; `/games/{uuid}/counter/incr` POST, `/games/{uuid}/counter?value=` PUT; `/games/{uuid}/lock?worker_id&ttl` GET acquire, DELETE release; `/games/{uuid}/expire?ttl` POST; outputs: `/output/count` GET (must precede `/{uuid}` route), `/output/{uuid}` GET 404-if-missing, PUT raw dict body; `/keys?pattern&prefix` GET; `/dbsize?prefix` GET; `/delete/keys/{key}?prefix` DELETE. `/rag/*` removed (404).
4. `rpg_ai_server/main.py`: boots logs — if `settings.search.configured`: "Search memory: configured (index=...)"; else warning "UPSTASH_SEARCH... missing — memory drain disabled".
5. `rpg_ai_server/requirements.txt`: replaced `upstash-vector>=1.1,<2.0` → `upstash-search>=0.1,<2.0`; removed `sentence-transformers>=3.0,<6.0`.

### Live verification (real DB)
- SDK roundtrip: upsert 3 docs (turn=1) → `query("goblin axe attack", top_k=2)` → top hit "The goblin king attacks with a rusty axe." score 0.875, second "A dragon sleeps on a mountain of gold." 0.0463 (real semantic ranking); export 3; restore 1; clear → remaining 0. Scratch sid `smoke-test-f8aQ3x` cleaned.
- ASGI tests + HTTP server (`uvicorn :8055`): `/memory/upsert` → 2 docs, `/memory/query` "owlbear wounded forest" → top hit correct (sniffed full JSON later: `score 0.5`), `/memory/clear` → export empty. Scratch sids cleaned.

---

## 2. Task: Redis unblock + full live E2E

- Old `.env` had `UPSTASH_REDIS_REST_URL-1`/`-2` (broken names) — fixed to `UPSTASH_REDIS_REST_URL`/`UPSTASH_REDIS_REST_TOKEN` (still pointed at dead host at the time).
- User provided new Redis (`handy-longhorn-80079`) → PING PONG → wired into `.env`.
- Live E2E (uvicorn :8055, real both DBs), per-step results:
  - health = ok; queue.length after push = 1; queue.pop.sid round-tripped; state.story GET = `{"value":"A ranger enters the cave."}`; counter.incr incremented (leftover from earlier aborted run); lock acquire=True, second attempt=False (after fix), release=True; output.count=1; output.get.story="You found a potion."; memory.query.top → "A horde of goblins brandishes rusty axes."; memory.export.count=2; memory.clear=True.
  - `GET /keys` with default pattern returned 0; `/dbsize` → 500 (Upstash restricts `KEYS`; non-blocking ecosystem limitation).
- All scratch keys/namespaces cleaned (`e2e-*`, `lk-u1`, `lock-probe:x`, `rag-smoke-9Kq1`).

---

## 3. Task: Lock bug — SDK False vs None

- Symptom (live E2E): second worker reported `acquired=True`.
- Root cause: `upstash_redis.AsyncRedis.set(..., nx=True, ex=ttl)` returns `False` when NX fails (not `None`). `acquire_lock` checked `result is not None` → always True.
- Fix: `rpg_ai_server/redis/client.py` line ~229 → `return bool(result)` (also correct for redis-py convention True/None).
- Regression tests: `tests/test_lock_client.py` (`_SdkBehavior` fake: set returns False when lock held; acquire/reject/release and wrong-worker release tests) — 4 assertions, 2 tests.
- Live re-verify: `acquire w1=True | attempt w2=False`.
- `release_lock`/`refresh_lock` compare `current == worker_id` (fine); note SDK `GET` missing → None.

---

## 4. Task: Web scenario play flow (built from scratch — `lib/scenarios.ts` was ORPHANED: zero callers)

### Discovery
- `app/game/[uuid]/` is a game *browser* (catalog: characters/maps/items from Supabase `lib/db.ts`), NOT gameplay UI.
- No chat/play surface existed anywhere (no SSE player, no /api/push consumers, no prompt UI).
- `lib/scenarios.ts` (registry CRUD, memory blob, `resolveEntry`, `shouldAutosave`) and `lib/ai-server-client.ts` were written but unused.
- The AI server has NO CORS middleware → the browser can never call `127.0.0.1:8000` directly → all calls must go through Next.js server-side routes.

### Files created/modified
1. `app/api/ai-server/[...path]/route.ts` — generic relay: GET/POST/PUT/DELETE, forwards query string + raw body, `AI_SERVER_URL` env (default `http://127.0.0.1:8000`), JSON responses or `{error}` 502. (Next 15 style: `params: Promise<{path?: string[]}>`.)
2. `lib/playClient.ts` — typed client over the proxy + memory route:
   - `queuePush(sid, data)` → POST `/api/ai-server/queue/push?uuid=..&data=<URL-encoded JSON>` (server takes `data` as a *query param* — `aiServer.queue.push` in the old client sent a body and would 422; `pushUrlEncoded` was correct);
   - `outputGet(sid)` → 404 → null; `outputCount()`; `queueLength()`;
   - `stateSetField(sid, field, value)` → PUT with `value=` JSON-string query param;
   - `counterIncr(sid)`; `memoryExport(sid)` → GET `/api/games/{sid}/memory`; `memoryRestore(sid, chunks)` → POST `{chunks}`; `memoryClear(sid)` → DELETE.
3. `components/game/ScenarioEntry.tsx` — registry screen: list (`listScenarios`), per-slot Enter (passed to route; restore decision is made by PlayScreen via blob presence), Delete (`deleteScenario`), New Adventure inline name form (`createScenario`, max 60 chars). Styling follows existing theme tokens (`border-border`, `text-accent`, `bg-background`, `text-text-muted`, `text-destructive`).
4. `components/game/PlayScreen.tsx` — the play UI:
   - State: `messages[{role,text}]`, `busy`, `error`, `exitOpen`, `sealed` (input locked while restoring).
   - Turn persistence: `turnRef` initialized from `localStorage rpg:turn:{sid}`; `lastConsumedRef` from `rpg:ready:{sid}` (story signature).
   - Mount effect: if `loadMemory(sid)` has `chunks.length > 0` → `memoryRestore(sid, chunks)` (refills shared Search index), then unseal.
   - `send(text)`: queuePush `{sid, prompt, turn}` → best-effort `stateSetField(sid,'prompt_history',text)` → `counterIncr(sid)` → poll loop: every 2 s `outputGet(sid)`; accept when `story` non-empty AND `!== lastConsumed` (engine overwrites `output:{sid}` per turn; dedupe prevents re-showing last turn's story); on accept: append assistant message, `turn += 1`, persist, **autosave every 10 turns** (`shouldAutosave` → `memoryExport` → `saveMemory` blob `{sid, saved_at, last_turn, chunks}` + `touchScenario`), clear interval. Timeout after 60 tries (~2 min) → error message.
   - Poll is resilient to mid-write reads (engine SETs a full JSON — if it throws a 500, keep polling; concurrent SET vs GET not atomic but retried).
   - Exit modal: **Save & Exit** → export → `saveMemory` blob + `touchScenario` + persist turn → `/play`; **Don't Save** → `memoryClear(sid)` + `clearMemory(sid)` → `/play`; **Keep Playing** → close. Both blocked while `busy` (prevents exporting mid-turn).
5. `components/game/PlayGate.tsx` — client wrapper: `getScenario(sid)`; missing → "Adventure not found" + link to `/play`; else renders PlayScreen.
6. `app/play/page.tsx` — entry (`ScenarioEntry`, router to `/play/{id}`).
7. `app/play/[sid]/page.tsx` — server component: `await params` → PlayGate (matches `game/[uuid]` page pattern).
8. `types/ai-server.ts` — `AiMemoryChunk{id, content: Record<string,unknown>, metadata?: Record<string,unknown>|null}` (was `{id, vector: number[], metadata}`); `AiMemoryHit extends AiMemoryChunk {score}`; `AiMemoryQueryResponse.hits: AiMemoryHit[]`.
9. `lib/ai-server-client.ts` — memory client: `query(namespace, query, topK)` → `{namespace, query, top_k}`; `upsert(namespace, documents)` → `{namespace, documents}`. (`restore` shape unchanged and compatible; still zero callers — available for a future retrieval panel.)
10. `lib/scenarios.ts` — comments only (blob is "search-memory blob").
11. Web `.env` — removed dead `UPSTASH_VECTOR_REST_URL/TOKEN` placeholders. (Web `.env`'s OWN Upstash Redis `rational-falcon...` is dead but unused by the RPG flow.)

### Verifications
- `npx tsc --noEmit` clean (after fixing `json()` helper to accept `Promise<Response>|Response`).
- `npm run build` OK — routes compiled: `/api/ai-server/[...path]`, `/api/games/[id]/memory`, `/play`, `/play/[sid]`.

---

## 5. Task: RAG read path (was MISSING — only drain/write existed)

### Discovery
- `grep rag_context` → nothing in agents; only `MemorySaver` matched "memory". Confirmed retrieval was never implemented despite REDIS_API.md describing it.

### File changes
1. `rpg_ai_server/schemas/state.py` — added `rag_context: str` (after `search_results`).
2. `rpg_ai_server/engine/orchestrator.py` — `initial_state["rag_context"] = ""`.
3. `rpg_ai_server/agents/node4_tool_agent/agent.py`:
   - imports: `from ...redis.vector_memory import GameMemory`
   - module-level `_memory: GameMemory | None = None`
   - `async def _retrieve_memories(uuid, prompt) -> str`: guard `settings.search.configured`; lazy singleton; `await _memory.query(uuid, prompt, top_k=settings.search.top_k)`; formats `[memory {i} | turn {turn} | relevance {score:.2f}]\n{text[:1500]}` per hit joined with blank lines; any Exception → log + `""` (agent keeps working).
   - Template `TOOL_AGENT_PROMPT_TEMPLATE` gained a `{memories}` section header "Previous memories from long-term story memory:" (after "Previous context/search results: {context}").
   - `node4_tool_agent`: `rag = await _retrieve_memories(state["uuid"], state.get("prompt", ""))`; template `.format(..., memories=rag)`; return `{"tool_results": [...], "rag_context": rag}`.
   - NOTE: `stat.level` assumed — `CharacterStats` default has `.level`.
4. Live smoke: seeded sid `rag-smoke-9Kq1` (2 docs, turn 4) → `_retrieve_memories(sid, 'weapons goblin king')` → hit1 relevance 0.88 (goblin king text), hit2 0.00 (cursed blade); cleared → remaining 0.

---

## 6. Task: Loop guards + engine pipeline (pre-existing, now re-verified in live run)

- Already implemented & unit-tested earlier: router cap (`ROUTER_MAX_PASSES=4`) + `remaining_steps` decrement + `conditional_passes`, recursion_limit=60, wall-clock 120 s timeout (`_run_graph` with `asyncio.wait_for` + lock keep-alive task every 10 s), graceful `GraphRecursionError` story (`GRACEFUL_ERROR_STORY` "A twisting mist swallows the scene..."), error sanitization (type-name only), `ToolCallLimitMiddleware` (import-guarded), context_summary/decision persisted per turn, `try_drain` never raises on memory failure.
- `GameOrchestrator.process_request`: lock-owning, load-or-seed state (`_build_initial_state` + `save_initial_state`), run graph, save `game_data/story/character_stats/context_summary/decision`, `try_drain(uuid, story)` after each turn (drain if major action keyword OR counter≥10; empty buffer clears; failure keeps story in hash).
- `MultiTaskEngine`: semaphore `max_concurrent_requests`, backpressure via `output_cache.memory_pressure_ok()` + `backoff_seconds`, QueueManager delayed-queue mover + retry/dead-letter (`MAX_RETRIES=3`, `backoff_delay(5*2^n)`).

---

## 7. Task: Middleware bug found in live run (FIXED)

- Live run error: `Node 4 tool agent failed: ToolCallLimitMiddleware.__init__() got an unexpected keyword argument 'max_total_tool_calls'`.
- Installed signature: `(self, *, tool_name=None, thread_limit=None, run_limit=None, exit_behavior='continue')`.
- Fix: `ToolCallLimitMiddleware(run_limit=settings.app.max_tool_calls)` in `agents/node4_tool_agent/agent.py` (kept the ImportError guard). Verified `node4 import OK`.

---

## 8. Live full-pipeline run — PARTIAL (user asked to skip to save time; processes stopped, cleaned)

- Booted `python -m rpg_ai_server.main` (upstash Redis connected, graph built, "Multi-task engine started").
- Pushed `live-t1`: `{"uuid":"live-t1","prompt":"I cautiously approach the ruined bridge and search for goblin tracks before crossing.","data":{"player_level":1}}` via `/queue/push` → engine picked it up: "Processing request UUID live-t1" → initial state saved → Node 5 (context injection) ran first → Router → Node 4 → **failed on middleware kwarg** (see Task 7) → Node 6 story generation failed (`'Tool Results'` because tool_results contained the error string) → Node 7 pushed fallback output `"The story continues... (generation error: 'Tool Results')"` → output persisted → drain attempted → "Request live-t1 completed successfully".
- Takeaways: full plumbing (queue→state→graph→output→drain) works live end-to-end; the only failure was the middleware kwarg (now fixed). Node 6 failure mode: when tool_results contains an error string, story gen errors out — possible future hardening: pass `tool_results` only when non-error.
- After fix, engine restarted (pid 18280) but the user asked to skip; processes stopped. NOT re-run.

---

## 9. Tests & docs

### Server tests (82 passing, `python -m pytest tests/ -q`)
- `tests/fakes.py`: `FakeSearchDoc{id,content,metadata}`, `FakeSearchIndex{upsert,search(query,limit,filter,reranking,...),fetch(ids|prefix),delete(ids|prefix|filter)}` with deterministic keyword-overlap score + `@metadata.sid = '<sid>'` filter parser; insertion-order tie-break; `FakeGamesClient` (hash/counter/lock), `FakeInputClient` (queue/delayed/dead/heartbeat), `FakeOutputClient`. Vector fakes removed.
- `tests/test_search_memory.py` (renamed from test_vector_memory.py): upsert_chunks count/shape/id-prefix, empty noop, root-text shortcut, invalid doc skip, query ranking + sid scoping + top_k + empty, export content/metadata/turn, export ignores other games, export empty, export↔restore roundtrip (ids preserved), restore empty noop, clear only one sid.
- `tests/test_game_state.py`: roundtrip save/load + expire, missing → None, initial state, drain below threshold (no upsert), drain at threshold (upserts to search, counter reset, story removed), major-action immediate upsert + detection in text + incident metadata (`is_incident`, `sid`, `turn`), no-memory keeps story, **memory failure keeps story** (`BoomIndex.upsert` raises), empty story clears buffer, lock lifecycle incl. refresh.
- `tests/test_redis_api.py`: health; memory upsert→export; empty documents; query hits + score + content; restore roundtrip; clear; rag endpoints 404; queue/state/output tests below.
- `tests/test_lock_client.py`: SDK-False regression (acquire/reject/release, wrong-worker release).
- `tests/test_chunking.py`: estimate_tokens, sentence split, overlap, hard split, single-char budget.
- Plus: queue backoff/DLQ, output, compression, router, orchestrator tests (pre-existing, still green).

### Web checks
- `npx tsc --noEmit` clean; `npm run build` clean.

### Docs
- `D:\AI agent\REDIS_API.md`: whole Game Memory section rewritten to Upstash Search (write/read paths, env vars, python sketch, filter syntax, why-not-Vector), scenario lifecycle (blob = text, no vectors; size ~200 KB; restore re-embeds server-side), API block (`/memory/query upsert export restore clear`), data-flow diagram line, FAQ #3.
- `D:\AI agent\README.md`: architecture diagram label, component table, RAG & Memory System section, env sample block, session lifecycle line.
- `D:\AI agent\PROGRESS.md`: master summary (this file's compact sibling).
- `D:\AI agent\compaction.md`: this file.

---

## Boot commands
- Engine: `python -m rpg_ai_server.main` (cwd `D:\AI agent`) — long-running; on Windows signal handlers unsupported → poll-based shutdown.
- API only: `python -m uvicorn rpg_ai_server.redis_api:app --port 8055` (same cwd; startup/shutdown via deprecated on_event).
- Graph compile check: `python -c "from rpg_ai_server.engine.graph_builder import build_game_graph; build_game_graph(None).compile()"`.
- Tests: `python -m pytest tests/ -q`.
- Web: `npm run dev` in `D:\deepslate dungeons` → play UI at `http://localhost:3000/play`; tsc `npx tsc --noEmit`; build `npm run build`.

## Known limitations / notes
- `/keys`, `/dbsize` on Upstash Redis: `KEYS` restricted → 500s; admin-only, non-blocking.
- `on_event` deprecation warnings in redis_api.py (FastAPI ≥0.107) — harmless.
- Web `.env` still holds a dead Upstash Redis pair (unused by the RPG flow) — safe to leave or remove.
- Node 6 story generation errors when node4 returns an error string in tool_results (observed live) — hardening option: node4 returns structured errors, or node6 ignores error entries.
- `output:{sid}` GET is not consumptive; client relies on story-string dedupe.
- Free-tier quota: Search DB call volume (upserts/query/delete) uncounted; watch daily limits.

## Remaining / optional
1. **Full live story run** (re-verify after middleware fix AND new SSL fix): boot engine → push turn (e.g. `live-final-1`) → poll `/output/{sid}` until a real story (expect 3 LLM calls, ~1-3 min) → check memory drain → cleanup keys/namespace.
2. Optional: `rag_context` also injected into node5/node6 (narrative continuity).
3. Optional: web "remembered memories" panel using `aiServer.memory.query`.
4. Optional: hardening node6 against error tool_results.

---

# SESSION LOG (17:00-17:40, 2026-08-14) — SSL blocker + fix + handoff

## CRITICAL FOR NEXT SESSION (this 20-min blocker last time)
- **Symptom 1** `rpg_ai_server/redis/client.py`: long-lived upstash_redis clients fail with
  `[SSL: UNSAFE_LEGACY_RENEGOTIATION_DISABLED]` → engine mover loop + main queue pop died,
  engine useless. **fresh clients (3 quick calls) worked FINE** → hard to reproduce with one-off
  SDK calls; ONLY appears on pooled/long-lived connections (Upstash edge requires legacy TLS
  renegotiation; Python 3.14 / OpenSSL 3.0.19 forbids it by default).
- **Symptom 2** after the TLS fix on one engine start it instead threw
  `[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate` at ~24s.
  **NOT reproduced on the identical later start (clean 13+ min). NOT explained.** See below.
- Env: `python --version` = 3.14.4, `ssl.OPENSSL_VERSION` = OpenSSL 3.0.19, `upstash_redis` = 1.7.0,
  httpx present. `ssl.OP_LEGACY_SERVER_CONNECT` IS available.

## The fix (IMPLEMENTED + LIVE-VALIDATED)
`rpg_ai_server/redis/client.py` — after `import httpx`, before `from upstash_redis import AsyncRedis`:
- `_legacy_ssl_context()`: `ssl.create_default_context()` then `ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT` (guarded by `hasattr`).
- `_LegacyTLSClient(httpx.Client)` / `_LegacyTLSAsyncClient(httpx.AsyncClient)`: subclasses that set `kwargs["verify"] = _legacy_ssl_context()` when `verify is None`, then `super().__init__(...)`.
- `_patch_httpx_legacy_tls()`: `httpx.Client = _LegacyTLSClient; httpx.AsyncClient = _LegacyTLSAsyncClient`, guard `if getattr(httpx,"Client",None) is _LegacyTLSClient: return`. Called at module import (line 43, right before `from upstash_redis import AsyncRedis`).
- **MUST use SUBCLASSES, NOT function wrappers.** First attempt used plain-func wrappers →
  broke `openai` (`class _DefaultHttpxClient(httpx.Client)` → `TypeError: argument 'code' must be code, not str`). Subclassing preserves class-ness so openai/langchain keep importing.

## Verification status
- ✅ `python -c "import rpg_ai_server.redis.client as c, httpx, openai"` → `Client patched True`,
  `AsyncClient patched True`, `openai import OK`. Graph compile OK.
- ✅ `engine_loop_repro.py` (temp): patched Input/Output/Games clients, `pop_request` +
  `pop_delayed_due` every 1 s → **92+ s ZERO errors** (file below).
- ✅ **LIVE ENGINE** (the last one I started): booted **17:27:17**, log at
  `C:\Users\YOUSSE~1\AppData\Local\Temp\opencode\engine_out.log`, **error-free for 13+ min** as of
  handoff (well past the 24 s and the old 9-min failure windows). Fix validated live.
- ⚠️ ONE unexplained anomaly: the intermediate engine start at 17:14:33 (SAME subclass-patched code)
  hit Symptom-2 CERTIFICATE_VERIFY_FAILED at 17:14:57. Never reproduced since; the clean 17:27:17 run
  supersedes it. **If cert errors recur, check:** whether some lib imported by `main.py` BEFORE
  `redis.client` reassigns `httpx.Client` (never confirmed), and Start-Process vs shell env
  (`SSL_CERT_FILE`/`SSL_CERT_DIR` were both None in shell).

## Previous runs this session (for Claude to avoid repeating the 20-min loop)
- 09:50-ish original engine (pre-fix): boot OK, mover + engine started failing ~9 min in.
- 17:14:33 engine: subclass patch loaded, but CERTIFICATE_VERIFY_FAILED at ~24 s (unexplained).
- 17:27:17 engine: **CURRENTLY RUNNING, clean.** Boot cmd: `python -m rpg_ai_server.main` (cwd `D:\AI agent`).
- Live story test (`live_story_test.py`, temp): pushed `live-final-1` to `input:queue` twice,
  polled `output:live-final-1` + `games:live-final-1:state` 5 min → **never processed (no state set)**
  both times. Push worked (queue len=1). Engine was NOT healthy during those pushes (SSL/cert dead),
  so this does NOT reflect a real failure — must RE-RUN story test on the clean engine.

## Handoff / resume checklist for Claude
1. **Leave the running engine up** (17:27:17, error-free). Watch its log for SSL ERRORs another ~10 min as final validation.
2. Re-run live story test: `python "C:\Users\YOUSSE~1\AppData\Local\Temp\opencode\live_story_test.py"` (sid `live-final-1`) → expect real story in ~1-3 min, then memory drain check + cleanup (script does all).
3. Remaining optional tasks re-verified/notes:
   - #2 `rag_context` node5/6: node4 now sets `rag_context` in state (see §5); node5/6 templates don't consume it yet — add a memory section.
   - #3 web memories panel: `lib/ai-server-client.ts` `query()` exists, zero callers today.
   - #4 node6 error-tool_results hardening: still open (§ Known limitations).
4. **Commit state (uncommitted)**: `git status` shows README.md, REDIS_API.md (+ plan/ copies), settings.py, node4 agent.py, graph_builder.py, multi_tasker.py, orchestrator.py, main.py, redis/client.py, game_state.py, redis_api.py, requirements.txt, schemas/state.py, + new vector_memory.py (untracked), tests/, PROGRESS.md, compaction.md. New Python deps this change: `upstash-search`, `httpx` (now imported directly).
5. `.env` (server + web) holds LIVE Upstash Search + Redis creds from §0 — do not commit/secrete.
6. Temp scripts live in `C:\Users\YOUSSE~1\AppData\Local\Temp\opencode\` (`live_story_test.py`, `engine_loop_repro.py`) — disposable.