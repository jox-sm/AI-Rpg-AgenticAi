# RPG AI Server — System Architecture & Plan

Two systems talk through **shared Redis** (Upstash). The AI server is a Python FastAPI server that does the actual AI agent processing. Next.js is the web server. Game memory lives in **Upstash Search** (a separate Upstash product) — no Chroma, no vector ops in Redis, no client-side embeddings.

---

## Redis Data Layout (shared between both servers)

```
# DB 0 — Queue & Coordination
input:queue                List   { uuid: session_id, prompt: string }
trigger:last               Str    unix timestamp of last FastAPI trigger
trigger:busy               Str    "1" while FastAPI is processing (TTL 30s)

# DB 1 — Game State (Hash, per plan §1)
games:{sid}:state          Hash   fields: player, allies, monsters,
                                  current_chunk, buildings, story (gzip),
                                  incidents (gzip), context_summary, etc.
games:{sid}:counter        Str    action count (INCR, RESET on drain)
games:{sid}:lock           Str    distributed lock (SET NX EX, plan C3)

# Output (DB 1, separate key per session)
output:{sid}               Str    AI output for current turn
                                  { story, tool_results, game_over? }
```

All `games:{sid}:*` keys get TTL reset to 1h on each user action.
State is a **Hash** (not a plain string) per the existing plan — Next.js must use HSET/HGETALL/HGET, not SET/GET. See plan/redisIntegration.md for canonical schema.

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

- **Write path:** on drain trigger (major action OR counter ≥ 10), the AI server splits story/incidents into chunks (token-budgeted, ~512 tokens, 32-token overlap) and upserts them — Upstash Search embeds server-side, so the client never sends vectors and no model runs locally.
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

A **scenario** = one user-chosen name + one game id (`sid`, embedded in every memory document). The player manages scenarios like save slots; memory survives the Redis 1h TTL because it lives locally. (Web app lives at `D:\deepslate dungeons` — client flow below is the contract it implements.)

**Client-side registry (localStorage):**
```
key:   rpg:scenarios
value: [ { id: "<uuid>", name: "My Dungeon Crawl", created_at, last_played_at } ]
key:   rpg:memory:{id}   → exported search-memory blob for that scenario
```

- The `sid` (scenario uuid) is the per-game scope in the shared `game-memory` index — the user-chosen name is only a label, so renaming never touches the documents.
- The exported blob is plain text (`id, content, metadata`) — restore re-embeds server-side on upsert, no clientside model.

**Entry flow (user enters the game):**
```
1. App reads rpg:scenarios from localStorage
2. Search by scenario id (uuid):
     a. Found + Redis state alive (within 1h) → resume live state directly
     b. Found + state expired   → recognize via uuid, then
        POST /memory/restore → upsert saved chunks into the namespace
        → AI server starts fresh state skeleton; memory works from turn 1
     c. Not found → "New game" screen → prompt for a name → create scenario
        (new uuid, empty namespace) → play
3. "New scenario" button (any time) → step 2c again — adds a new slot with a new sid
```

**Exit flow (player leaves):**
```
1. Player clicks Exit → modal popup: "Save this game?"  [Save] [Don't save]
2. Save        → GET /memory/export/{sid} → write rpg:memory:{id}
                 → update rpg:scenarios (last_played_at) → toast "Game saved"
3. Don't save  → optional DELETE /memory/clear (wipe namespace) — slot stays,
                 advances are lost
4. Documents are never destroyed on exit — only on real game_over (or explicit delete)
```

**Autosave — every 10 messages:**
- The drain already fires at `counter ≥ 10`; it sets `autosave` flag in the drained state. The client reads it after the action → auto-exports → refreshes `rpg:memory:{id}` in the background. Worst case on crash: 10 messages lost.
- The same `rpg:memory:{id}` blob is used by the resume flow (2b), so autosave and manual save never diverge.

- **Size check:** ~200 chunks × ~1KB JSON (text + metadata, no vectors) ≈ 200KB — fits localStorage (5MB) comfortably.
- **Why no vectors in the blob?** Upstash Search embeds server-side; restore = plain upsert of text, no model/cost on resume.

---

## Data Flow

```
Client (browser)            Next.js                          AI Server (FastAPI)
      │                        │                                    │
      │  Enter game            │                                    │
      │───────────────────────►│                                    │
      │                        │  generate session_uuid             │
      │                        │  write initial state via HSET      │
      │                        │  HSET games:{sid}:state            │
      │                        │    player   → '{...}'              │
      │                        │    story    → ''                   │
      │                        │    (EXPIRE 1h)                     │
      │                        │                                    │
      │  Send action           │                                    │
      │  POST /api/games/[uuid]/play {prompt, sid}   │
      │───────────────────────►│                                    │
      │                        │  RPUSH input:queue {uuid:sid,prompt}
      │                        │  EXPIRE games:{sid}:state 3600     │
      │                        │                                    │
      │                        │  checkTrigger() — queue≥5 OR 1s?  │
      │                        │  ┌── NO → return 202               │
      │                        │  └── YES → POST /trigger ────────►│
      │                        │           (NX lock trigger:busy)   │
      │                        │                                    │
      │                        │          RENAME input:queue → :processing
      │                        │          for each item:
      │                        │            HGETALL games:{sid}:state
      │                        │            decompress story
      │                        │            memory retrieval (Upstash Search)
      │                        │            agent workflow
      │                        │            HSET patched fields
      │                        │            SET output:{sid} = delta
      │                        │          DEL input:queue:processing
      │                        │          DEL trigger:busy
      │                        │                                    │
      │                        │  POST /api/games/worker ◄─────────│
      │                        │    { uuid: sid }                  │
      │                        │                                    │
      │                        │  SSE push to open connection      │
      │                        │  (no Redis event key, no polling) │
      │                        │                                    │
      │  SSE ◄─────────────────│                                    │
      │  (open connection,     │                                    │
      │   real-time push)      │                                    │
      │                        │                                    │
      │  GET output:{sid}      │                                    │
      │  merge delta, render   │                                    │
      │  snapshot sessionStorage│                                   │
      │  every 10min           │                                    │
```

---

## Session Lifecycle

### New Session
1. User clicks play on a game → `GET /game/{game_uuid}`
2. Frontend checks `sessionStorage` for cached session
3. If miss → generate `session_uuid` (crypto.randomUUID())
4. Fetch game data from DB (chars, maps, items)
5. `SET games:{sid}:state` with initial JSON blob (TTL 1h)
6. Store `{ sid, game_uuid }` in sessionStorage

### Existing Session
1. `sessionStorage` has `{ sid, game_uuid }`
2. `GET games:{sid}:state` from Redis via Upstash
3. If exists → resume game
4. If expired/not found → treat as new game

### TTL Refresh
Every user action resets TTL to 1h on `games:{sid}:*` keys.
After 1h inactivity → session auto-cleans from Redis.

---

## Trigger System

```
onPlayerAction():
  1. RPUSH input:queue {uuid, prompt}
  2. touchTTL(sid)
  3. checkTrigger()

checkTrigger():
  1. len = LLEN input:queue
  2. if len == 0 → return
  3. busy = GET trigger:busy
  4. if busy == "1" → return (already processing)
  5. last = GET trigger:last (unix seconds)
  6. now = Date.now() / 1000
  7. shouldFire = (len >= 5) OR (now - last >= 1)
  8. if shouldFire → fireTrigger()

fireTrigger():
  1. SET trigger:busy = "1" (EX 30) — prevent double-trigger
  2. POST http://ai-server:8000/trigger
  3. SET trigger:last = now
```

---

## Next.js API Routes

### POST /api/games/[uuid]/play
- Accepts: `{ prompt: string, sid: string }`
- Pushes to `input:queue`
- Calls `checkTrigger()`
- Returns 202

### GET /api/games/[uuid]/stream
- SSE endpoint
- Polls `games:{sid}:event` every 200ms
- Pushes events to client
- Closes on error/disconnect

### POST /api/games/worker
- FastAPI callback
- Accepts: `{ uuid: session_id }`
- Writes to `games:{sid}:event`
- SSE picks it up

---

## Next.js Client Library

### hooks/useGamePlay.ts
```
useGamePlay(uuid):
  sendAction(prompt) → POST /api/games/{uuid}/play
  state ← SSE /api/games/{uuid}/stream
  snapshot to sessionStorage every 10min
```

### lib/ai-redis.ts
```
pushPlayerAction(sid, prompt)
readGameState(sid)
touchSessionTTL(sid)
readOutput(sid)
incrActionCounter(sid)
```

### lib/game-trigger.ts
```
checkTrigger()   → queue >=5? 1s passed?
fireTrigger()    → POST /trigger to FastAPI
```

---

## Implementation Order

1. `lib/ai-redis.ts` — Redis operations (uses existing Upstash client)
2. `lib/game-trigger.ts` — Trigger logic
3. `app/api/games/[uuid]/play/route.ts` — Player action endpoint
4. `app/api/games/[uuid]/stream/route.ts` — SSE endpoint
5. `app/api/games/worker/route.ts` — FastAPI callback
6. `hooks/useGamePlay.ts` — Client hook
7. `types/play.ts` — Types

---

## AI Server FastAPI Endpoints (reference)

```
Health:
  GET  /health               → {"status":"ok"}

Trigger (NEW — atomic drain per plan §5):
  POST /trigger              → RENAME input:queue → :processing
                               for each: HGETALL → agent → HSET → output
                               POST /worker callback to Next.js
                               DEL :processing + trigger:busy

Queue (input:):
  POST /queue/push         → RPUSH (Next.js writes directly to Redis, not this)
  GET  /queue/pop          → LPOP (used by /trigger internally)
  GET  /queue/length       → LLEN

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
- Queue push fails       → return 500, prompt lost (retry on client)
- Trigger POST fails     → trigger:busy auto-expires in 30s, retries on next action
- Worker POST fails      → FastAPI retries (3 attempts, backoff)
- SSE connection drops   → client reconnects, polls last known event
- Graph loop runaway     → guarded: router pass cap + RemainingSteps + recursion_limit=60
                          → GraphRecursionError → graceful "the story grows quiet" output
                          → see plan/loops.md
```

---

## Game Architecture (from graphify-out)

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

### 5. Missing `/trigger` endpoint — to be added

The FastAPI `redis_api.py` needs a `POST /trigger` endpoint. Per the plan's drain pattern (atomic rename):

```python
@app.post("/trigger")
async def trigger():
    # 1. Get the busy lock (redundant check — Next.js already set it)
    busy = await redis.get("trigger:busy")
    if not busy:
        return {"error": "not triggered"}, 409

    # 2. Atomic drain: RENAME input:queue → input:queue:processing
    try:
        await redis.rename("input:queue", "input:queue:processing")
    except:
        return {"ok": True, "items": 0}  # queue empty

    # 3. Process all items
    items = []
    while True:
        item = await redis.lpop("input:queue:processing")
        if not item:
            break
        items.append(json.loads(item))

    for item in items:
        sid = item["uuid"]
        # load state
        state = await games.hgetall(f"games:{sid}:state")
        # run orchestration...
        # write output + state...
        await redis.set(f"output:{sid}", json.dumps(output), ex=3600)
        # callback to Next.js
        await callback_nextjs(sid)

    # 4. Cleanup
    await redis.delete("input:queue:processing")
    await redis.delete("trigger:busy")
    return {"ok": True, "items": len(items)}
```

### 6. FastAPI callback URL — env var ✔

`NEXTJS_WEBHOOK_URL` env var on the AI server (`http://nextjs-server:3000/api/games/worker`).

### 7. Next.js trigger URL — env var ✔

`AI_SERVER_URL` env var on Next.js (`http://ai-server:8000`). Only referenced in `fireTrigger()`.

### 8. State write conflict — no race ✔

New sessions get their initial state written *before* the first action is queued. The only time the AI server writes state is after processing that action. Since the lock (`games:{sid}:lock`) prevents concurrent processing, there's no race. The AI server's `process_request` loads existing state or builds it from scratch if missing.

### 9. sessionStorage size — fine ✔

~50-200KB per snapshot is fine for 2MB Safari limit. Multiple saves accumulate only while `sessionStorage` lives (tab open). 10min snapshot = 1 save in storage at a time.

### 10. Adding `/trigger` endpoint ✔

Confirmed — I'll add `POST /trigger` to `redis_api.py` with the atomic rename drain pattern from the plan. Also need a `/trigger` route in Next.js that sets `trigger:busy` and calls the AI server.

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

**15. Game end — cleanup?**

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
