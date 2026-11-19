# RPG AI Server — System Architecture & Plan

Two systems talk through **shared Redis** (Upstash). The AI server is a Python FastAPI server that does the actual AI agent processing. Next.js is the web server. Game memory lives in **Upstash Search** (a separate Upstash product) — no Chroma, no vector ops in Redis, no client-side embeddings.

---

## Redis Data Layout (shared between both servers)

```
# DB 0 — Queue & Coordination
input:queue                List   { uuid: session_id, prompt: string }
                                  (engine polls this continuously; no trigger key needed)
input:queue:delayed        ZSet   retry-scheduled items (score = due timestamp)
input:queue:dead           List   poison/exhausted items (inspect manually)

# DB 1 — Game State (Hash, per plan §1)
games:{sid}:state          Hash   fields: player, allies, monsters,
                                  current_chunk, buildings, story (gzip),
                                  incidents (gzip), context_summary,
                                  game_data, character_stats, etc.
games:{sid}:counter        Str    action count (INCR, RESET on drain)
games:{sid}:lock           Str    distributed lock (SET NX EX, plan C3)

# Output (DB 1, separate key per session, TTL 1h)
output:{sid}               Str    AI output for current turn
                                  { uuid, game_data, story, context_summary,
                                    tool_results, game_over, timestamp }
                                  `timestamp` = server write time — primary
                                  turn-change marker for web polling
```

All `games:{sid}:*` keys get TTL reset to 1h on each user action.
State is a **Hash** (not a plain string) per the existing plan — Next.js must use HSET/HGETALL/HGET, not SET/GET. See plan/redisIntegration.md for canonical schema.

> The legacy `trigger:last` / `trigger:busy` keys are no longer part of the
> contract — the engine owns the queue via polling (see Trigger System).

---

## Game Memory (Upstash Search — replaces the old RAG/Vector plan)

One **AI-powered hybrid search index** (semantic 75% + full-text 25% default), shared by all games and scoped per session via the `sid` field. There are no namespaces in Upstash Search: each document carries `sid` in content **and** metadata, and ids are prefixed `{sid}:` so export/clear can enumerate by prefix/filter.

```
# Upstash Search index (one shared index, no Chroma, no DB 2)
index:          game-memory
document id:    "{sid}:{turn}:{idx}:{uuid8}"
content:        { sid: <uuid>, text: "<chunk text>" }
metadata:       { sid: <uuid>, turn, index, is_incident, ts }
```

- **Write path:** on drain trigger (major action OR counter ≥ 25), the AI server splits story/incidents into chunks (token-budgeted, ~512 tokens, 32-token overlap) and upserts them — Upstash Search embeds server-side, so the client never sends vectors and no model runs locally.
- **Read path:** `node4_tool_agent` builds a text query from current context → `POST /memory/query {namespace, query}` → hybrid search scoped by filter `@metadata.sid = '<sid>'` → hits (`id, score, content, metadata`) injected as `rag_context` into the LLM prompt.
- **Why Upstash Search instead of Upstash Vector / Redis Search?** AI-hybrid relevance with zero client embedding infra: no sentence-transformers, no dimension planning, no per-game namespaces. Upstash Redis Search is Tantivy full-text only; Upstash Vector would still require an embedding step client-side or a second model service.
- **Filter syntax** is SQL-like; metadata keys are prefixed `@metadata.` (e.g. `@metadata.sid = 'x' AND @metadata.is_incident = 1`).

**Env vars (AI server):**
```bash
UPSTASH_SEARCH_REST_URL=your-search-url
UPSTASH_SEARCH_REST_TOKEN=your-search-token
SEARCH_INDEX_NAME=game-memory
SEARCH_TOP_K=3
SEARCH_RERANKING=false
SEARCH_SEMANTIC_WEIGHT=0.75
SEARCH_INPUT_ENRICHMENT=true
SEARCH_CHUNK_MAX_TOKENS=512
SEARCH_CHUNK_OVERLAP_TOKENS=32
```

**Drop-in sketch (python `upstash-search`):**
```python
from upstash_search import Search

search = Search(settings.search.upstash_search_url, settings.search.upstash_search_token)
index = search.index(settings.search.index_name)

# write: on drain
index.upsert(documents=[
    {"id": f"{sid}:{turn}:{i}:{uuid4().hex[:8]}", "content": {"sid": sid, "text": chunk}, "metadata": {"sid": sid, "turn": turn, "index": i}}
    for i, chunk in enumerate(chunks)
])

# read: on retrieval
hits = index.search(query=query_text, limit=5, filter=f"@metadata.sid = '{sid}'")
context = "\n---\n".join(h.content["text"] for h in hits)
```

**HTTP contract (see §API):** the web client proxies through the AI server (`/memory/*`) — it never talks to Upstash directly.

---

## Scenario Lifecycle — Named Save Slots

A **scenario** = one user-chosen name + one game id (`sid`, embedded in every memory document). The player manages scenarios like save slots; memory survives the Redis 1h TTL because the AI side keeps it in the shared `game-memory` index. (Web app lives at `D:\deepslate dungeons` — client flow below is the contract it implements.)

**Client-side vault (in-memory zustand, `stores/game-saves.ts`) — NOT localStorage:**
```
scenarios: [ { id, name, created_at, last_played_at } ]     // save slots
memories:  { [sid]: { sid, saved_at, last_turn, chunks } }  // exported blobs
turns:     { [sid]: number }                                // turn counters
```

- The vault lives for the **lifetime of the tab** (deliberately un-persisted). Durability is explicit and user-driven via the **Save button** (below), which downloads a whole-vault JSON snapshot; the scenario list imports files back.
- The `sid` (scenario uuid) is the per-game scope in the shared `game-memory` index — the user-chosen name is only a label, so renaming never touches the documents.
- The exported blob is plain text (`id, content, metadata`) — restore re-embeds server-side on upsert, no clientside model.

**Turn-1 note:** turn counters reset to 0 in a fresh tab (no file imported). This is advisory — the engine keeps its own turn/state in `games:{sid}:state`; only the client-side "Turn N" display and per-turn payload restart.

**Entry flow (user enters the game):**
```
1. Scenario list reads the zustand vault (live subscription)
2. Play/{sid} gate resolves the scenario id (uuid):
     a. Found + Redis state alive (within 1h) → resume live state directly
     b. Found + vault has saved chunks → push them back:
        POST /memory/restore → upsert(saved chunks into the namespace)
        → AI server starts fresh state skeleton; memory works from turn 1
     c. Not found → catalog "Play" CTA creates the slot client-side
        (uuidv7 sid, seed carried via sessionStorage → GameRequest.data)
3. Import from file (any time): scenario list loads a save file →
   vault merge (known sids overwritten, unknown added, capped to 20 slots)
```

**Exit flow (player leaves):**
```
1. Player clicks Exit → modal: "Save this adventure?"  [Save & Exit] [Don't Save] [Keep Playing]
2. Save & Exit → GET /memory/export/{sid} → vault.memories[sid] refresh
                → touch slot (last_played_at) → memory lives on in the AI index
3. Don't Save  → DELETE /memory/clear (wipe namespace) + vault blob dropped
4. Documents are never destroyed on exit — only on real game_over (or explicit delete)
```

**The Save button (file snapshot) — `lib/saveFile.ts`:**
```
PlayScreen "Save":
  1. GET /memory/export/{sid} → refresh vault.memories[sid]  (freshest AI memory)
  2. buildSavesSnapshot() → { kind: "deepslate-saves", version: 1, exported_at,
     scenarios, memories (array), turns }  ← whole vault in one file
  3. Browser download: deepslate-saves-YYYYMMDD-HHmmss.json
Scenario list "Have a save file? Import it":
  readSavesFile(File) → validate kind/version → importSnapshot into the vault
  → imported runs resume normally (restore path above works from the vault)
```

**Autosave — every 10 turns:**
- PlayScreen auto-exports every 10 turns into the vault (`AUTOSAVE_EVERY_TURNS`), so the Save button is never the only copy while playing. Autosave and manual save never diverge — both write the same vault blobs; the AI-side index always holds the ground truth until the file is downloaded.

- **Size check:** ~200 chunks × ~1KB JSON (text + metadata, no vectors) ≈ 200KB per run — the snapshot file scales with run count; no local quota concerns anymore.
- **Why no vectors in the blob?** Upstash Search embeds server-side; restore = plain upsert of text, no model/cost on resume.

---

## Data Flow (as implemented)

```
Browser              Next.js (relays)                AI Server (FastAPI + engine)
   │                        │                                    │
   │  /game/[uuid] page     │                                    │
   │── "Play" ─────────────►│                                    │
   │                        │  (client) uuidv7 → sid, scenario    │
   │                        │  registered, GameSeed → sessionStorage
   │                        │                                    │
   │  /play/{sid}           │                                    │
   │── send(prompt) ───────►│                                    │
   │                        │  POST /api/ai-server/queue/push     │
   │                        │    uuid=<sid>, prompt, data         │
   │                        │    {turn, world_seed?, campaign?}   │
   │                        │          │ (Clerk session + allowlist)
   │                        │          ▼                          │
   │                        │          POST /queue/push ─────────►│
   │                        │          RPUSH input:queue          │
   │                        │                                    │
   │                        │                                    │  MultiTaskEngine polls
   │                        │                                    │  input:queue → lock →
   │                        │                                    │  load-or-seed state →
   │                        │                                    │  LangGraph v2 run →
   │                        │                                    │  save_state → SET output:{sid}
   │                        │                                    │  (story, game_data, game_over,
   │                        │                                    │   timestamp) — TTL 1h
   │                        │                                    │
   │  poll (2s interval)    │                                    │
   │── GET output/{sid} ───►│── GET /output/{sid} ──────────────►│
   │◄─ {story, timestamp} ──│◄───────────────────────────────────│
   │                        │                                    │
   │  render story          │                                    │
   │  autosave every 10     │  GET /api/games/[id]/memory        │
   │  turns via memory      │  → AI /memory/export → Upstash Search
```

Turn-change detection: the poller compares `output.timestamp` against the last
consumed one (mount-local refs, no persistence); on a fresh mount nothing was
consumed yet, so any output older than the client's send epoch is treated as a
stale leftover from a previous run (2s clock-skew slack). If an output has no
timestamp it falls back to comparing the story string.

---

## Session Lifecycle

### New Session
1. User clicks play on a game → `GET /game/{game_uuid}`
2. Frontend checks `sessionStorage` for cached session
3. If miss → generate `session_uuid` (crypto.randomUUID())
4. Fetch game data from DB (chars, maps, items) — kept, not written to Redis
5. First turn's `GameRequest.data` carries the seed (see Session Seeding below);
   the **engine seeds `games:{sid}:state` itself on turn 1** (allowlist merge)
6. Store slot in the zustand vault (`stores/game-saves.ts` — in-memory; durable
   copies exist via the Save button file or the AI-side index)

### Existing Session
1. The zustand vault has the scenario slot (or a save file was imported)
2. `GET games:{sid}:state` from Redis via Upstash
3. If exists → resume game
4. If expired/not found → treat as new game (restore memory first: POST /memory/restore)

### TTL Refresh
Every user action resets TTL to 1h on `games:{sid}:*` keys.
After 1h inactivity → session auto-cleans from Redis.

### Session Seeding from a Catalog Game
A play session started from a game page (`/game/[uuid]` → Play button) injects
the game's creative payload into turn 1; the engine preserves it verbatim into
`game_data` (client fields in `request.data` are kept):

```
Browser                          AI engine (turn 1, _build_initial_state)
─────────────────────────────────────────────────────────────────────────
sessionStorage rpg:seed:{sid} →  GameRequest.data = {
  { game_id, name,                  turn: 1,
    description, characters,        world_seed: <game_id>,      ← same world for
    maps, items }  (slimmed —       campaign: { name,             every session of
  no image blobs)                      description,               the same game
                                       characters, maps, items }
                                 }
```

- `world_seed` precedence: `data.world_seed || request.uuid` — a catalog game
  seeds a stable shared world; a plain scenario session seeds its own world
  from the sid.
- The seed is one-shot: `sessionStorage rpg:seed:{sid}` is consumed on the
  first `send()` only.
- `data.campaign` is a map/prompts hint (characters/maps/items with names +
  descriptions); the engine's mechanics/grid still run on their own data model.
- Transport: sessionStorage (`rpg:seed:{sid}`), written by the game page
  (`lib/gameSeed.ts`), read+consumed by PlayScreen before the first push.

---

## Trigger System (retired — engine-owned queue)

The trigger machinery (`trigger:busy` NX lock, `/trigger` drain, `lib/game-trigger.ts`,
webhook callback) is **retired**. The engine (`MultiTaskEngine.run`) polls
`input:queue` continuously (~100 ms idle cadence), so a push is picked up
without any client-side trigger. This removes the one race the old design
could not fix: a drain racing the engine and stealing real player turns.

`POST /trigger` still exists as an **advisory status probe** (back-compat): it
returns queue/dead-letter lengths and consumes nothing:

```
POST /trigger →
  {
    "ok": true,
    "queued": len(input:queue),
    "dead_lettered": len(input:queue:dead),
    "note": "engine polls input:queue directly; no items consumed here"
  }
```

---

## Next.js API & Client (as implemented)

### AI-server relay — `app/api/ai-server/[...path]/route.ts`
Generic server-only relay to the FastAPI gameplay surface. Requires a signed-in
Clerk session (re-checked server-side via `validateJWTMiddleware`) and only
forwards the gameplay allowlist; everything else → 403:

```
allowed:
  GET   /health
  POST  /trigger                 (advisory probe)
  POST  /queue/push
  GET   /queue/length
  GET   /output/count
  GET   /output/{sid}
  GET|PUT /games/{sid}/state/{field}
  POST  /games/{sid}/counter/incr

blocked (admin/destructive/queue internals): /keys, /dbsize, /delete/keys/*,
  /queue/pop, /queue/delayed/*, /queue/dead/*, /games/{sid}/lock,
  /games/{sid}/expire, PUT /output/{sid}, …
```

### Memory relay — `app/api/games/[id]/memory/route.ts`
`GET` → `/memory/export/{sid}`, `POST {chunks}` → `/memory/restore`,
`DELETE` → `/memory/clear?namespace=sid`. Same Clerk-session requirement.

### Memory configuration note
`/memory/*` and the engine's memory drain need `UPSTASH_SEARCH_REST_URL` /
`UPSTASH_SEARCH_REST_TOKEN` in `rpg_ai_server/.env` (Upstash console → Search
→ index). Without them the API answers `503 {"detail": "Game memory is not
configured…"}` on those endpoints (gameplay itself is unaffected; story
generation works, memory/saves are disabled).

### Admin delete semantics (gotcha)
`GET /keys?pattern&prefix` and `DELETE /keys/{key:path}?prefix` select the
client by `prefix` (`input` / `games` / `output`) — the client adds its own
namespace, so **the key path must NOT include it**: the state hash lives in
Redis as `games:{sid}:state`, but the API call is
`DELETE /keys/{sid}:state?prefix=games`. Passing `games:{sid}:state` deletes a
non-existent `games:games:{sid}:state` (harmless `ok:false`).

### Session routes (web's own catalog APIs)
`/api/games`, `/api/games/[id]` (+`/patches`, `/memory`), `/api/push`,
`/api/push/pushGames`, `/api/drain`, `/api/workers` — the game-creation/fetch
pipeline below ("Game Architecture"); unrelated to the AI turn flow.

### Play client — `lib/playClient.ts`
```
queuePush(sid, GameRequest)   → POST /api/ai-server/queue/push
outputGet(sid)                → GET  /api/ai-server/output/{sid}  (404 → null)
stateSetField(sid, field, v)  → PUT  /api/ai-server/games/{sid}/state/{field}
counterIncr(sid)              → POST /api/ai-server/games/{sid}/counter/incr
memoryExport(sid)             → GET  /api/games/{sid}/memory
memoryRestore(sid, chunks)    → POST /api/games/{sid}/memory
memoryClear(sid)              → DELETE /api/games/{sid}/memory
```
UI consumer: `components/game/PlayScreen.tsx` (send → push + counterIncr →
poll every 2 s for `output:{sid}` → render story; game_over still delivered via
`output.game_over`).

### Entry point — `app/game/[uuid]/game-detail.tsx`
Play button → `uuidv7` sid + `createScenarioWithId` (scenario registry slot) +
`saveGameSeed` (sessionStorage) → navigate to `/play/{sid}` (see Session Seeding).

---

## AI Server FastAPI Endpoints (reference)

```
Health:
  GET  /health               → {"status":"ok"}

Trigger (advisory probe — the engine consumes input:queue itself):
  POST /trigger              → {"ok": true, "queued": n, "dead_lettered": n,
                                 "note": "engine polls input:queue directly;
                                          no items consumed here"}
  Retired drain semantics (RENAME → per-item processing → webhook) removed:
  they raced the engine and stole real player turns.

Queue (input:):
  POST /queue/push         → RPUSH (Next.js writes directly to Redis, not this)
  GET  /queue/pop          → LPOP (used by /trigger internally)
  GET  /queue/length       → LLEN

  Queue items are Pydantic `GameRequest` objects:
    { uuid, prompt, data, images, timestamp }
  `uuid` is the session id (same key as the `games:{uuid}:state` hash).
  `sid` is accepted as a read-compatible alias of `uuid`.
  Missing both → poison request → dead-letter + retry path.

Game State (games:{sid}:state — HASH per plan §1):
  GET  /{sid}/state        → HGETALL (read full state)
  GET  /{sid}/state/{f}    → HGET single field
  PUT  /{sid}/state/{f}    → HSET single field
  POST /{sid}/counter/incr → INCR
  POST /{sid}/expire       → EXPIRE

Output (output:{sid}):
  GET  /{sid}              → GET
  PUT  /{sid}              → SET with EX

Memory (Upstash Search, shared index filtered by sid):
  POST /memory/query       → hybrid search (query text, namespace=sid, top_k)
  POST /memory/upsert      → upsert documents {id?, content, metadata?} (namespace=sid)
  GET  /memory/export/{sid} → dump all docs for sid (Save / autosave, see §Scenario Lifecycle)
  POST /memory/restore     → upsert saved blob back under sid (resume flow)
  DELETE /memory/clear     → wipe all docs for sid (game_over / "Don't save")
```

---

## Error Handling

```
- Queue push fails       → relay returns 5xx, client surfaces error (retry on user)
- Poll timeout           → client gives up after ~2 min: "AI server didn't respond
                           — check it's running on :8000"
- Engine item fails      → QueueManager.handle_failure: retry → input:queue:delayed,
                           poison/exhausted → input:queue:dead (dead letter)
- Graph loop runaway     → guarded: router passes=3, 60s wall, budget/LLM-call force-exit to story
                           → see engine/graph_v2.py (`_budget_exhausted`, `react_router_node`)
                          → GraphRecursionError → graceful "the story grows quiet" output
                          → see plan/loops.md
- Death                  → engine saves final state; output.game_over=true;
                           web closes the game (death contract below)
```

---

## Game Architecture (from graphify-out)

> NOTE: third-party analysis output for a different repo's backend — not this system; kept for reference only.

Graph analysis of the existing game backend (320 files indexed).

### Game Pipeline Abstraction

```
Game Creation Pipeline:
  create_form → api_convertUrl → api_push → ConvertGameImages → pushGames

Backend Game Processing (cohesion 0.09, 36 nodes):
  processGamesQueue → warmUpCache → getGamesPaginated → insertGame
  validateJWTMiddleware → classifyError → GamesInsert

Games API Cache & Drain (cohesion 0.17, 20 nodes):
  GET/POST cache routes → CACHE_KEYS → ensureCachePrimed
  getCachedGameIds → getGameFromCache → mergePendingLikes

Game Fetch Pipeline (Client) (cohesion 0.13, 30 nodes):
  getGameWithBatchQueue → pollGameResult → requestGameFetch
  useErrorHandler → errorToast → warningToast → ClassifiedError

MongoDB Operations:
  GamesInsert (processGamesQueue) → patch-applier (applyGamePatches)
  Mongoose schema → batch inserts → atomic updates

Redis Cache Layer:
  queue.ts (Upstash client) → cache-warmup (warmUpCache)
  setGameInCache → getGameFromCache → mergePendingLikes/mergePendingLikesBatch

Error Handling Spine:
  classifyError → used by GamesInsert, cache-warmup, db,
  jwt-validate, patch-applier, useAuth, useIdempotentRequest

Drain Pattern:
  queue.drain() → atomic RENAME → LRANGE → DEL → batch insert
  Triggered by: GET /api/drain, auto-trigger from /api/games
```

### Key Files (game backend)

| File | Lines | Role |
|------|-------|------|
| `lib/queue.ts` | 19 | Upstash Redis client singleton |
| `lib/cache-warmup.ts` | 155 | Cache priming + game CRUD in Redis |
| `lib/GamesInsert.ts` | 23 | Queue drain → MongoDB insert |
| `lib/db.ts` | ~80 | PostgreSQL queries (getGames, insertGame) |
| `lib/patch-applier.ts` | 115 | JSON Patch on MongoDB |
| `utilities/queue.ts` | 46 | Generic drain (atomic rename) |
| `utilities/pull.ts` | 42 | drainLikes + drainGames |
| `utilities/gameFetchPipeline.ts` | 212 | Batch fetch queue for game detail |
| `utilities/hotnessCache.ts` | 384 | Binary-sorted hotness cache (top 1000) |
| `app/api/games/route.ts` | 104 | Paginated games list + drain trigger |
| `app/api/games/[id]/route.ts` | 47 | Game detail (standard cache) |
| `app/api/games/[id]/route-gamepage.ts` | 59 | Game detail (hotness cache) |
| `app/api/games/[id]/patches/route.ts` | 32 | POST JSON patches to MongoDB |
| `app/api/drain/route.ts` | 45 | Drain endpoint (games + likes) |
| `app/api/push/route.ts` | ~50 | Push game to Redis queue |
| `app/api/push/pushGames/route.ts` | ~50 | Push extended data to MongoDB queue |
| `models/games/mongodb/schema.ts` | ~30 | Mongoose schema |
| `models/games/mongodb/client.ts` | ~20 | MongoDB connection |

---

## Resolved Issues (based on plan/redisIntegration.md)

> ⚠️ **Historical design record.** Items 1–4, 6–7 and the SSE/webhook Q&A below
> describe the *original* trigger+SSE design. That design was never shipped in
> the web app; the implemented turn flow is push-to-queue + engine polling +
> 2 s output polling (see "Data Flow (as implemented)"). `/trigger` semantics
> changed to an advisory probe — see "Trigger System" and item 5 below.

### 1. State type — Hash not String ✔

Per `plan/redisIntegration.md` §1: `games:{uuid}:state` is definitively a **Hash** (HGETALL/HSET/HDEL). The AI server already uses Hash. Next.js must also use Hash:

```typescript
// Init: write each field as a Hash field
await redis.hset(`games:${sid}:state`, {
  player: JSON.stringify(initialPlayer),
  story: compress(""),
  incidents: compress(""),
  context_summary: "",
});
await redis.expire(`games:${sid}:state`, 3600);

// Read: HGETALL returns all fields
const state = await redis.hgetall(`games:${sid}:state`);
// state.player = JSON string, state.story = gzip+base64
```

The plan also uses patch-based writes — only HSET fields that changed. Next.js on init writes the full skeleton (player, empty story, empty incidents). The AI server patches individual fields each turn.

### 2. SSE route — sid from query param ✔

`GET /api/games/[uuid]/stream?sid=xxx` — the client sends `sid` as a query parameter. The route handler uses it to identify the session. The `[uuid]` is the game UUID (for auth/ownership checking).

### 3. No Redis polling for SSE — push-based ✔

Worker callback writes directly to the open SSE connection — no Redis polling at all.

```typescript
// lib/sse-connections.ts — in-memory map
const connections = new Map<string, Response>();

// POST /api/games/worker — FastAPI callback
export async function POST(req: Request) {
  const { uuid } = await req.json();
  const output = await redis.get(`output:${uuid}`);
  const sse = connections.get(uuid);
  if (sse) {
    const encoder = new TextEncoder();
    sse.body?.getWriter().write(encoder.encode(`data: ${output}\n\n`));
  }
}

// GET /api/games/[uuid]/stream — SSE setup
export async function GET(req: Request) {
  const sid = new URL(req.url).searchParams.get("sid")!;
  const stream = new ReadableStream({ ... });
  connections.set(sid, new Response(stream, sseHeaders));
  // on disconnect: connections.delete(sid)
}
```

### 4. No event overwrite — direct push ✔

Solved by #3 — no Redis event key, no polling, no overwrite. Each worker callback directly writes to the open SSE connection for that session. Multiple events in quick succession are queued by the stream writer.

### 5. `/trigger` endpoint — implemented (see `redis_api.py`)

⚠️ Semantics changed (2026-10): the atomic rename drain was **removed** — it
raced the engine loop for `input:queue` and could eat real player turns while
writing placeholder `"(processed)"` stories. Current behavior is a passive
status probe:

```python
@router.post("/trigger")
async def trigger():
    c = await _get_input()
    queued = await c.queue_length()
    dead = await c.client.llen("input:queue:dead")
    return {
        "ok": True,
        "queued": queued,
        "dead_lettered": dead,
        "note": "engine polls input:queue directly; no items consumed here",
    }
```

### 6. FastAPI callback URL — env var ✔ (retired — dead code)

`NEXTJS_WEBHOOK_URL` pointed at `/api/games/worker`, a route that never existed
in the web app. The webhook post was removed together with the drain trigger.

### 7. Next.js trigger URL — env var ✔ (retired)

`AI_SERVER_URL` env var on Next.js (`http://ai-server:8000`). Only referenced in `fireTrigger()`.

### 8. State write conflict — no race ✔

New sessions get their initial state written *before* the first action is queued. The only time the AI server writes state is after processing that action. Since the lock (`games:{sid}:lock`) prevents concurrent processing, there's no race. The AI server's `process_request` loads existing state or builds it from scratch if missing.

### 9. sessionStorage size — fine ✔

~50-200KB per snapshot is fine for 2MB Safari limit. Multiple saves accumulate only while `sessionStorage` lives (tab open). 10min snapshot = 1 save in storage at a time.

### 10. `/trigger` endpoint ✔ (superseded)

Originally the atomic rename drain (409 without `trigger:busy`, per-item poison
guard, cleanup). Replaced by the advisory probe — see item 5 and "Trigger System".
The web never calls it; the engine owns the queue.

### State & Data

**1. Initial state format — what JSON shape does Next.js write?**

Write a minimal bootstrap state:
```json
{
  "session": { "sid": "...", "game_uuid": "...", "created_at": 1718000000 },
  "character_stats": {
    "level": 1, "health": 100, "max_health": 100,
    "mana": 50, "max_mana": 50, "strength": 10,
    "skills": { "combat_offense": 1, "combat_defense": 1, "magic": 1 },
    "carry_capacity": 50, "current_load": 0
  },
  "inventory": [],
  "skills": [
    { "name": "Basic Attack", "level": 1, "cooldown": 0, "max_cooldown": 1 },
    { "name": "Dodge", "level": 1, "cooldown": 0, "max_cooldown": 2 }
  ],
  "grid": null,
  "story": "",
  "relationships": [],
  "tool_results": [],
  "context_summary": "",
  "game_data": {
    "world": { "name": "", "seed": "", "grid_size": 6, "regions": [], "current_events": [] }
  }
}
```

The AI server's orchestrator (`_build_initial_state`) already generates `character_stats`, the 6×6 world grid, and starter skills when it sees `grid` is `null`. So just write the skeleton — the AI server fills in the world on first trigger.

**2. AI server output format — what's in `output:{sid}` vs `games:{sid}:state`?**

- `output:{sid}` → The **narrative result** of the current action only: `{ "story": "...", "tool_results": [...] }`. The LLM-generated story prose, plus any mechanic results (damage dealt, items gained, XP earned).
- `games:{sid}:state` → The **full persistent state** after the action: `character_stats`, `inventory`, `skills`, `grid`, `relationships`, `story` (appended), `game_data`, `context_summary`.

SSE should push `output:{sid}` (the event/delta). The **client merges** it: replaces story, updates state. On reconnect (SSE drop), the client reads `games:{sid}:state` to rebuild from scratch.

**3. Chunks/memory on init — does Next.js write initial memory chunks?**

No — the AI server handles the entire memory pipeline internally. `try_drain()` in `GameStateManager` compresses story text, splits it into chunks, and upserts to the shared Upstash Search index (filtered by `sid`). Upstash embedds server-side. Next.js never touches memory keys.

### Session & Identity

**4. Route ambiguity — `/api/games/[uuid]/play` — game UUID or session UUID?**

**Game UUID** (from DB). The client sends `sid` in the POST body:
```json
{ "prompt": "attack goblin", "sid": "a1b2c3d4-e5f6-..." }
```

**5. Auth — does `/play` require JWT?**

Yes, for consistency with your existing API routes. Sessions are **tied to a user** (the JWT subject). A user can have **multiple sessions** across different games (one per game UUID). The `sid` is unique per session.

**6. Two tabs, same game — independent or shared?***

**Independent.** Each tab generates its own `sid`. Each has its own `games:{sid}:state` in Redis. This prevents state corruption from concurrent writes. The player effectively has two parallel save files.

### Queue & Trigger

**7. Queue item depth — what's in the payload?**

```json
{ "uuid": "sid", "prompt": "I swing my sword at the goblin", "timestamp": 1718000000 }
```

No `action_type` — the AI agent classifies the action via its system prompt. The LLM reads the prompt and decides what skill/tool to use.

**8. Race condition on trigger — two concurrent calls?**

Use `SET trigger:busy NX EX 30`. The `NX` flag makes it atomic — only one wins. The second caller sees `busy == "1"` and skips. FastAPI's `/trigger` should also `GET trigger:busy` first and return 409 if not set.

**9. Processing timeout — what if processing takes >30s?**

FastAPI must **periodically refresh `trigger:busy`** while processing:
```python
async def _refresh_busy():
    while processing:
        await redis.set("trigger:busy", "1", ex=30)
        await asyncio.sleep(15)
```
Alternative: use a longer TTL (e.g., 120s) on `trigger:busy`. Given your queue batches are at most ~5 items and each graph run takes ~5-15s, 60s is safe.

### Error Recovery

**10. Crash mid-processing — items lost from queue?**

Yes — LPOP removes items immediately. Two options:
- **Use the atomic rename pattern** like your existing `utilities/queue.ts`: `RENAME input:queue input:queue:processing` → batch process → `DEL input:queue:processing`. On crash, you inspect `input:queue:processing` manually.
- **Accept the risk** — at-most-once with 3 retry limit is already your design choice. LPOP'd but unprocessed items are equivalent to a failed retry exhausting its limit. Since the player retries on the client side (they see the 202 and wait), they can re-send the prompt.

I'd go with **option 1** (atomic rename) — cheap, already exists in your codebase.

**11. Worker callback failure — Next.js never notified?**

FastAPI should retry `POST /api/games/worker` with exponential backoff (3 attempts, 1s/3s/9s). If all fail, log the error and move on. The SSE client will time out after its 200ms polling interval and eventually re-connect, re-reading `games:{sid}:state` on reconnect.

### SSE & Client

**12. SSE serverless limits — Vercel timeout?**

Use **Edge Runtime** for the SSE route (`export const runtime = 'edge'`). Edge functions have longer timeouts and can maintain SSE connections. Or use polling as fallback: `useGamePlay` reads `games:{sid}:state` every 2s when SSE fails.

**13. SSE reconnect — does it need last event ID?**

No. On reconnect, `useGamePlay` reads the full `games:{sid}:state` (GET output or state Redis key) and replaces local state entirely. Events are not sequenced — the latest state is always authoritative.

**14. sessionStorage snapshot — what's saved?**

The full `games:{sid}:state` JSON blob. On page reload:
1. Read snapshot from sessionStorage → render immediately (optimistic)
2. Fetch fresh `games:{sid}:state` from Redis
3. If diff → merge and re-render
4. If snapshot is stale / session expired → show loading state

### Lifecycle

**15. Game end — cleanup? (death contract)**

When the player dies, the AI server still uploads the final state (normal save path), and the turn output carries `game_over: true` (mirrored as `game_data.player_dead` and `game_data.character_stats.is_dead`). The frontend closes the game on `game_over` — no polling needed.

On game over (death, victory, or explicit quit), push a special event to SSE: `{ "type": "game_over", "reason": "..." }`. The AI server can signal this via `output:{sid}` containing `"game_over": true`. Cleanup by TTL expiry — don't explicitly DEL keys. The Next.js client shows a "Game Over" screen and the sessionStorage cache is cleared.

### Batch & Callback

**16. Multi-session batch callback — one POST or many?**

**Many** — one `POST /api/games/worker { "uuid": sid }` per session. Each session's output is written to its own `games:{sid}:event` key. The SSE for each sid picks up its own event.

**17. State vs event payload — what does SSE push?**

SSE polls `games:{sid}:event`. When an event is found:
1. Read `output:{sid}` → get `{ "story": "...", "tool_results": [...] }`
2. Send that to the client as the SSE event data
3. Delete `games:{sid}:event` (or let the next poll overwrite)
4. Client merges the delta into local state

On SSE reconnect, skip `games:{sid}:event` and go straight to `games:{sid}:state` for a full state sync.

**18. Client-side merge strategy — replace or merge?**

**Replace.** SSE pushes `output:{sid}` which contains `{ "story", "tool_results" }`. The client replaces `localState.story` and appends to `localState.tool_results`. For the full state (`games:{sid}:state`), **replace everything** — the AI server always writes the complete authoritative state.

**19. Event overwrite race — SSE misses an event?**

Acceptable. The latest `output:{sid}` and `games:{sid}:state` always represent the most recent turn. The client always converges to the latest state. No event IDs needed.

### UI & Rendering

**20. State transition animation?**

Your call. Options:
- **Highlight diffs:** compare new vs previous `character_stats.health`, flash red/green on change
- **Fade in story:** the new story paragraph fades/slides in
- **Just re-render:** simplest, least code

**21. sessionStorage snapshot — optimistic render or wait?**

**Optimistic render.** Show the snapshot immediately while fetching fresh state from Redis. This makes page reloads feel instant. If Redis returns an error or expired session, fall back to the game select screen.

### Testing

**22. Test strategy?**

- **Integration test with local Redis:** spin up a local Redis (or use `redis-mock` for most tests), run the AI server's queue/state operations against it
- **Mock FastAPI `/trigger`:** in Next.js tests, mock `fetch("http://ai-server:8000/trigger")` to return 200
- **E2E with Playwright:** connect to a test AI server (can be a simplified version that returns canned responses)
- **SSE unit test:** verify the SSE route emits events when `games:{sid}:event` is set
