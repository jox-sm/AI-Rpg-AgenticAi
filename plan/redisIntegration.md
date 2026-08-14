# Redis Integration Plan

## Overview

Redis (Upstash) serves as the **central nervous system** between the web server and the AI game server. It handles game state persistence and request queuing (2 logical databases / key prefixes on a single Upstash instance). **Game memory is not stored in Redis** — narrative retrieval uses **Upstash Vector** (dense cosine index, one namespace per session). No Chroma, no external worker, no DB 2.

---

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   Web Server    │         │   AI Game Server │         │  Upstash Vector  │
│   (Next.js)     │         │   (LangGraph)    │         │  (game memory)   │
│                 │         │                  │         │                  │
│ User message →  │  RPUSH  │ LPOP queue →     │  embed  │ upsert           │
│ input:queue     ├────────►│ processes →      ├────────►│ namespace={uuid} │
│                 │         │ HSET state DB1   │         │                  │
│                 │◄────────┤                  │◄────────│ query(top_k=5)   │
│ reads response  │  GET    │ memory retrieval │  query  │ inject           │
│ from DB 1       │         │ via Vector       │         │ rag_context      │
└─────────────────┘         └──────────────────┘         └──────────────────┘
        │                           │
        └───────────────────────────┼───────────────────────────┐
                                    │                           │
                          ┌─────────▼─────────┐                 │
                          │   Upstash Redis    │                 │
                          │                    │                 │
                          │  DB 0: input:queue │                 │
                          │  DB 1: games:state │                 │
                          └────────────────────┘                 │
                                                                │
                          ┌────────────────────────────────────▼──┐
                          │  Upstash Vector — dense index, 384-dim│
                          │  cosine, namespace per session {uuid} │
                          └───────────────────────────────────────┘
```

---

## Key Structure

### Redis DB 0 — Queue & Coordination
```
input:queue              → List (RPUSH/LPOP) - pending game requests
input:queue:delayed      → Sorted Set - retry with backoff
input:queue:dead         → Sorted Set - failed after max retries
workers:{id}:heartbeat   → String - worker health check (TTL 15s)
```

### Redis DB 1 — Game State (TTL sliding window)
```
games:{uuid}:state       → Hash - current game state (patched per field)
games:{uuid}:lock        → String - distributed lock (TTL 30s, NX)
games:{uuid}:counter     → Integer - action counter for drain trigger
games:{uuid}:coord:{x}_{y} → Integer - coordinate→chunk index mapping
```

### Game Memory (Upstash Vector — replaced the old DB 2 rag staging)
```
Vector index            → dense, 384-dim (all-MiniLM-L6-v2), COSINE
vector id               → "{uuid}:chunk:{idx}"  (sequential chunk index)
namespace               → "{uuid}"  (per-game scoping, up to 100)
metadata                → { uuid, chunk_index, turn, ts, is_incident, text }
```

- **Write (drain):** every 10 actions or major event → decompress story/incidents from DB 1 → `split_into_chunks()` → embed → `index.upsert(vectors, namespace=uuid)`
- **Read:** `node4_tool_agent` builds a context query → `index.query(vector, top_k=5, include_metadata=True, namespace=uuid)` → `rag_context` injected into the LLM prompt
- **Why Upstash Vector instead of Redis DB 2 + Chroma?** Upstash Redis has no vector search (its `SEARCH.*` is Tantivy full-text only); Chroma meant a second external DB with its own uptime/billing. Upstash Vector is the same auth model as Upstash Redis, free tier (200M vectors×dims, 10k queries/day), and per-request pricing beyond that.

### State Hash Fields (DB 1)

```
HGET games:{uuid}:state player          → JSON entity
HGET games:{uuid}:state allies          → JSON array
HGET games:{uuid}:state monsters        → JSON array
HGET games:{uuid}:state current_chunk   → JSON (center + surrounding)
HGET games:{uuid}:state buildings       → JSON array
HGET games:{uuid}:state story           → Gzip-compressed JSON string
HGET games:{uuid}:state incidents       → Gzip-compressed JSON string
```

---

## 1. TTL Strategy & Data Lifecycle

### TTL by Key Type

| Key Pattern | DB | TTL | Reason |
|-------------|----|-----|--------|
| `games:queue` | 0 | **No TTL** | Queue items processed then deleted |
| `games:{uuid}:state` | 1 | **1 hour** (sliding) | Active game session, refreshed on every action |
| `games:{uuid}:lock` | 1 | **30 seconds** | Processing lock, auto-release |

**Upstash Vector has no TTL** — memory lives as long as the namespace exists. Namespace = **scenario uuid** (user-chosen name is only a client label in `localStorage["rpg:scenarios"]`). Deletion happens only on `game_over: true`, stale-state sweep, or explicit "Don't save" exit — an exit with "Save" keeps vectors intact for resume. This replaces the old `rag:*` 1h TTL dance (the staging keys no longer exist).

### Data Freshness Rules

```
On every user action:
  ├── Refresh games:{uuid}:state TTL → 1h (sliding window)
  ├── INCR games:{uuid}:counter
  ├── If counter ≥ 10 OR action is major → drain to memory (Upstash Vector)
  └── Queue items deleted after processing (no TTL needed)

On game end or player quits:
  ├── State expires naturally after 1h of inactivity
  ├── Last drain already pushed pending text to memory
  └── If player returns within 1h: state still alive, resume instantly

Drain trigger (every 10 actions OR major action):
  ├── Decompress story/incidents (gzip)
  ├── split_into_chunks() → embed (384-dim) → upsert to Vector namespace={uuid}
  ├── HDEL games:{uuid}:state story
  ├── HDEL games:{uuid}:state incidents
  └── RESET games:{uuid}:counter → 0
```

---

## 2. What Lives in Redis

### A. Queue Item (games:queue)

Each item is a JSON object pushed by the web server:

```json
{
  "uuid": "game-uuid-abc123",
  "player_action": "attack goblin",
  "timestamp": 1718800000
}
```

### B. Game State (games:{uuid}:state)

The full game state, stored as JSON. Only includes the current chunk (center + 8 surrounding = 3x3 grid), not the entire map:

```json
{
  "uuid": "game-uuid-abc123",

  "player": {
    "entity_id": "p-player-001",
    "type": "player",
    "level": 7,
    "xp": 2450,
    "xp_to_next_level": 3200,
    "stats": {
      "health": 100, "max_health": 100,
      "hunger": 80, "thirst": 60,
      "sleep": 90, "tiredness": 10,
      "karma": 50,
      "strength": 12, "agility": 8, "intelligence": 6,
      "endurance": 10, "perception": 7, "charisma": 5
    },
    "equipment": {
      "weapon": "i-shadow-dagger",
      "armor": { "chest": "i-iron-chestplate", "legs": "i-leather-leggings", "boots": "i-leather-boots" },
      "accessory": "i-iron-amulet"
    },
    "rune_slots": {
      "weapon": { "total": 2, "filled": 1, "runes": ["r-flame-01"] },
      "armor": { "total": 1, "filled": 0, "runes": [] }
    },
    "position": { "x": 5, "y": 10, "depth": 0 },
    "skills": {
      "combat": { "level": 3, "xp": 450, "xp_next": 800, "stat_bonus": { "damage": 6, "crit_chance": 0.05 } },
      "mining": { "level": 1, "xp": 120, "xp_next": 300, "stat_bonus": { "mining_speed": 0.1 } },
      "crafting": { "level": 2, "xp": 280, "xp_next": 500, "stat_bonus": { "craft_quality": 0.08 } },
      "stealth": { "level": 0, "xp": 0, "xp_next": 100, "stat_bonus": {} }
    },
    "perks": ["iron_stomach", "keen_eye"],
    "status_effects": [],
    "inventory_weight_current": 12.5,
    "inventory_weight_max": 50.0,
    "death_count": 0,
    "play_time_seconds": 7200,
    "biome_history": ["plain", "volcano"],
    "achievements": ["first_kill", "first_craft"]
  },

  "allies": [
    {
      "entity_id": "e-blacksmith-01",
      "type": "worker",
      "name": "Hrogir Ironhand",
      "profession": "blacksmith",
      "hp": 80, "max_hp": 80,
      "stats": { "strength": 14, "intelligence": 8 },
      "skills": { "blacksmithing": 85, "crafting": 70 },
      "position": { "x": 6, "y": 11, "depth": 0 },
      "relationship": "loyal",
      "mood": "neutral"
    }
  ],

  "monsters": [
    {
      "entity_id": "e-skeleton-007",
      "type": "monster",
      "name": "Skeleton Archer",
      "hp": 40, "max_hp": 40,
      "damage": 12, "range": 8,
      "behavior": "patrol",
      "senses": { "sight": 10, "hearing": 6, "smell": 0 },
      "aggression": 0.7,
      "flee_threshold": 0.2,
      "stats": { "strength": 8, "agility": 12 },
      "resistances": { "physical": 20, "fire": 0 },
      "weaknesses": { "holy": 2.0 },
      "position": { "x": 8, "y": 12, "depth": 0 },
      "loot_table": [
        { "item_id": "i-bone", "qty": "1d4", "chance": 0.8 },
        { "item_id": "i-bow", "chance": 0.15 }
      ]
    },
    {
      "entity_id": "e-goblin-012",
      "type": "monster",
      "name": "Goblin Raider",
      "hp": 20, "max_hp": 20,
      "damage": 6, "range": 1,
      "behavior": "aggressive",
      "senses": { "sight": 8, "hearing": 5, "smell": 3 },
      "aggression": 0.9,
      "flee_threshold": 0.3,
      "stats": { "strength": 8, "agility": 14 },
      "pack_behavior": { "min": 2, "max": 5, "formation": "loose" },
      "position": { "x": 9, "y": 13, "depth": 0 },
      "loot_table": [
        { "item_id": "i-gold", "qty": "1d6", "chance": 0.7 },
        { "item_id": "i-rusty-dagger", "chance": 0.2 }
      ]
    }
  ],

  "current_chunk": {
    "center": {
      "x": 5, "y": 3,
      "biome": "dark_forest",
      "blocks": [
        {
          "x": 0, "y": 0, "depth": 0,
          "block_id": "b-grass-001", "biome": "dark_forest",
          "weight": 1.0,
          "durability": { "current": 5, "max": 5, "mining_threshold": 1 },
          "trap": { "is_trap": false, "is_hidden": false },
          "items": [],
          "entities": ["e-skeleton-007"],
          "physics": { "temperature": 20, "wetness": 30, "fire_resistance": 5, "electricity_resistance": -1, "air_resistance": 20, "shock_resistance": 0, "melt_temperature": 200 }
        },
        ...
      ],
      "weather": "fog",
      "time_of_day": "dusk"
    },
    "surrounding": [
      {
        "x": 4, "y": 2, "biome": "dark_forest",
        "blocks": [...],
        "weather": "fog",
        "entities": ["e-wolf-003"]
      },
      { "x": 5, "y": 2, "biome": "dark_forest", "blocks": [...] },
      { "x": 6, "y": 2, "biome": "dark_forest", "blocks": [...] },
      { "x": 4, "y": 3, "biome": "dark_forest", "blocks": [...] },
      { "x": 6, "y": 3, "biome": "dark_forest", "blocks": [...] },
      { "x": 4, "y": 4, "biome": "swamp", "blocks": [...] },
      { "x": 5, "y": 4, "biome": "swamp", "blocks": [...] },
      { "x": 6, "y": 4, "biome": "swamp", "blocks": [...] }
    ]
  },

  "buildings": [
    {
      "building_id": "bld-tavern-001",
      "type": "social",
      "occupies_chunks": [{ "x": 5, "y": 3 }, { "x": 6, "y": 3 }],
      "entrance": { "x": 5, "y": 3, "depth": 0 },
      "interior_chunk_id": "int-tavern-001",
      "npcs": ["e-barkeep-01", "e-bard-01"],
      "services": ["rest", "food", "drink", "information", "trade"],
      "ambience": { "sound": "crowd_chatter", "music": "tavern_theme", "lighting": "candlelight" },
      "weather_protection": 1.0,
      "inside": false
    }
  ],

  "story": "VGhleSBzdW1ib25lZCB0aGUgd29sdmVz...",
  "incidents": "QSBzaWxlbnQgY2xhbXIgZXJ1cHRlZCBmcm9t..."
}
```

---

### C. Game Memory (Upstash Vector — replaces RAG staging in Redis)

No staging in Redis anymore. On drain, the AI server embeds and upserts directly:

```python
from upstash_vector import Index

index = Index(url=os.environ["UPSTASH_VECTOR_REST_URL"],
              token=os.environ["UPSTASH_VECTOR_REST_TOKEN"])

vectors = [
    (f"{uuid}:chunk:{i}", vector, {"uuid": uuid, "chunk_index": i,
                                   "turn": turn, "is_incident": False})
    for i, vector in enumerate(embeddings)  # 384-dim floats
]
index.upsert(vectors=vectors, namespace=uuid)

# retrieval (node4_tool_agent):
hits = index.query(vector=query_embedding, top_k=5,
                   include_metadata=True, namespace=uuid)
rag_context = "\n---\n".join(h["metadata"].get("text", "") for h in hits)
```

---

## 3. String Compression Strategy

Only `story` and `incidents` are compressed — everything else stays as normal JSON.

### Why Compress?

| Field | Treatment | Reason |
|-------|-----------|--------|
| `story` | Gzip-compressed | Long narrative text (20k-50k tokens) → 60-80% size reduction |
| `incidents` | Gzip-compressed | Long narrative text → 60-80% size reduction |
| `player` | Normal JSON | Structured, small |
| `allies` | Normal JSON | Structured, small |
| `monsters` | Normal JSON | Structured, small |
| `current_chunk` | Normal JSON | Structured, small |
| `buildings` | Normal JSON | Structured, small |

Narrative text compresses extremely well (high repetition, common words, predictable structure). With gzip at default level, story/incidents typically shrink by 60-80%. This is far better than base64 which expands by +33%.

### In Redis

```
games:{uuid}:state = {
  "uuid": "abc123",
  "player": { ... },                    ← full player entity schema
  "allies": [ ... ],                    ← worker/NPC entity schemas
  "monsters": [ ... ],                  ← monster entity schemas
  "current_chunk": {
    "center": { "x": 5, "y": 3, "biome": "...", "blocks": [...], "weather": "fog" },
    "surrounding": [ {...}, {...}, ... ]  ← 8 surrounding chunks (3x3 grid)
  },
  "buildings": [ ... ],                 ← buildings in current chunks
  "story": "<gzip-compressed bytes as JSON string>",
  "incidents": "<gzip-compressed bytes as JSON string>"
}
```

### Compression Strategies Compared

| Method | Ratio (narrative text) | Speed | Redis-friendly | Best For |
|--------|----------------------|-------|----------------|----------|
| **gzip** (level 6) | 60-80% reduction | Fast decompress, moderate compress | Yes (binary-safe) | General use, best ratio |
| **zstd** (level 3) | 65-85% reduction | Very fast both ways | Yes (binary-safe) | High-throughput, better ratio |
| **lz4** | 50-65% reduction | Extremely fast | Yes (binary-safe) | Latency-critical reads |
| **snappy** | 50-60% reduction | Extremely fast | Yes (binary-safe) | Google ecosystem |
| Base64 | **-33% expansion** | Fast | Yes | Avoid — increases size |

**Recommendation**: Use **zstd** (Zstandard) at compression level 3. It offers the best ratio/speed trade-off for narrative text and has excellent Python bindings (`pyzstd`). gzip is the safe fallback (built into Python, no dependencies).

### In Redis (stored as base64-encoded compressed bytes)

Since Redis Hash values must be valid UTF-8 strings, store compressed bytes as base64:

```
Field            Content                                    Size
─────            ───────                                    ────
story            <gzip-compressed bytes → base64 string>    ~25-40% of original
incidents        <gzip-compressed bytes → base64 string>    ~25-40% of original
player           normal JSON                                ~1KB
```

The compression + base64 combined still achieves **60-80% net reduction** vs raw text, because gzip's 60-80% compression far outweighs base64's +33% expansion.

### Implementation

```python
import gzip, json, base64

def compress_text(text: str) -> str:
    """Compress narrative text for Redis storage."""
    compressed = gzip.compress(text.encode("utf-8"), compresslevel=6)
    return base64.b64encode(compressed).decode("ascii")

def decompress_text(encoded: str) -> str:
    """Decompress narrative text from Redis storage."""
    compressed = base64.b64decode(encoded)
    return gzip.decompress(compressed).decode("utf-8")

# Storage: compress before HSET
state["story"] = compress_text(story_text)
state["incidents"] = compress_text(incidents_text)

# Retrieval: decompress after HGET
story_text = decompress_text(state["story"])
incidents_text = decompress_text(state["incidents"])
```

### Size Comparison (20k-token story = ~80KB)

| Method | Size | Ratio |
|--------|------|-------|
| Raw JSON string | 80,000 bytes | 100% |
| JSON + JSON escaping | ~80,200 bytes | ~100% |
| Base64 only | ~106,700 bytes | **+33%** |
| **gzip + base64** | **~16,000-32,000 bytes** | **20-40% of original** |
| **zstd + base64** | **~12,000-28,000 bytes** | **15-35% of original** |

---

## 4. Data Flow - Step by Step

### Phase 1: Request Intake (DB 0)

```
1. User sends action via web server
2. Web server RPUSH to games:queue (DB 0):
   RPUSH games:queue '{"uuid":"abc","player_action":"attack"}'
3. Web server returns 202 Accepted to user
```

### Phase 2: Worker Polling (DB 0 → DB 1)

```
AI server worker polls with LPUSH/LPOP:

LPOP games:queue  ← non-blocking, returns null if empty

On receive:
  ├── Decode JSON from queue
  ├── SETNX games:{uuid}:lock {worker_id} NX EX 30  ← lock game
  ├── If lock failed → RPUSH back (another worker is handling it)
  ├── HGETALL games:{uuid}:state
  ├── Decompress story and incidents (gzip → string)
  ├── Inject into LangGraph state
  └── Begin processing
```

### Phase 3: AI Processing

```
LangGraph pipeline (based on world rules):

1. State Injection:
   ├── Decompress story/incidents from gzip
   ├── Load player entity, allies, monsters
   ├── Load current_chunk (center + 8 surrounding)
   └── Load buildings in current area

2. World Simulation:
   ├── Dijkstra pathfinding (block weights, terrain costs)
   ├── Block physics (temperature, wetness, fire spread, water flow)
   ├── Weather effects (movement penalties, damage modifiers)
   ├── Time of day (spawning, visibility)
   └── Environmental hazards (traps, lava, acid)

3. Entity AI (LangGraph state machines):
   ├── Monster behavior: patrol → detect → chase → attack → flee
   ├── Pack tactics: coordinate attacks, flank, surround
   ├── NPC schedules: day/night routines, trading, quests
   ├── Combat intelligence: target weaknesses, use environment
   └── Adaptation: learn player tactics, change strategies

4. Combat Resolution:
   ├── Damage calculation (stats, equipment, resistances, weaknesses)
   ├── Status effects (poison, bleed, frozen, stunned)
   ├── Loot drops on kill
   ├── XP gain, level up checks
   └── Karma changes

5. Story & Incidents:
   ├── LLM generates narrative from state changes
   ├── Log significant events (kills, discoveries, trades)
   ├── Update story/incidents strings
   └── Set is_major flag if event qualifies (death, level_up, quest_complete, boss_kill, new_biome)

Output:
  ├── Updated player entity (stats, position, inventory, xp)
  ├── Updated monster entities (hp, position, status)
  ├── Updated ally entities (mood, relationship)
  ├── Updated current_chunk (block states, entity positions)
  ├── New story segment (gzip-compressed)
  └── New incidents (gzip-compressed)
```

### Phase 4: Patch-Based Writes + Drain Check (DB 1 → Upstash Vector)

```
After processing, patch what changed and check drain trigger:

Player changed?
  └── HSET games:{uuid}:state player '{...}'

Monster damaged?
  └── HSET games:{uuid}:state monsters '[...]'

Chunk blocks changed?
  └── HSET games:{uuid}:state current_chunk '{...}'

Story/incidents updated?
  └── HSET games:{uuid}:state story "<gzip+base64>" incidents "<gzip+base64>"

Always:
  ├── EXPIRE games:{uuid}:state 3600  ← refresh TTL (sliding 1h)
  ├── DELETE games:{uuid}:lock        ← release processing lock

Drain check:
  ├── INCR games:{uuid}:counter
  ├── If counter ≥ 10 OR LLM flagged is_major:
  │     ├── Decompress story/incidents (gzip → text)
  │     ├── split_into_chunks() → embed (384-dim)
  │     ├── upsert to Upstash Vector, namespace={uuid}
  │     ├── HDEL games:{uuid}:state story
  │     ├── HDEL games:{uuid}:state incidents
  │     └── SET games:{uuid}:counter 0
  └── Else: skip drain
```

### Why Patch-Based?

| Approach | Bandwidth | Latency | Consistency |
|----------|-----------|---------|-------------|
| Full SET (old) | ~5KB every action | Slow | Safe |
| Patch HSET (new) | ~200-500B per field | Fast | Safe |

Only 1-3 fields change per action (player position, 1-2 monster hp, maybe story). No reason to reupload chunks, allies, buildings that didn't change.

### Phase 5: Memory Ingestion (in-process → Upstash Vector)

```
No more external Chroma worker — the AI server embeds on drain:

  1. Decompress story/incidents (gzip → string)
  2. Split into 10k-token chunks (shared split_into_chunks())
  3. Generate embeddings with sentence-transformers (384-dim, all-MiniLM-L6-v2)
  4. index.upsert(vectors=[("{uuid}:chunk:{i}", vec, metadata)], namespace=uuid)
  5. Optional retry on transient API errors (Upstash Vector is eventually
     consistent — newly upserted vectors may take a moment to be queryable)
```

Embedding runs in the AI server process (or a tiny aux task) — no queue, no staging keys, no TTL bookkeeping.

---



---

## 5. Worker Polling Configuration

### Strategy: Drain-Loop

LPOP non-blocking in a tight loop, sleeping when empty:

```python
POLL_INTERVAL = 0.5     # seconds between polls when queue empty
DRAIN_LIMIT = 5         # max items per drain cycle

async def worker_loop():
    while True:
        items = []
        # Drain up to DRAIN_LIMIT items
        for _ in range(DRAIN_LIMIT):
            result = await redis.lpop("games:queue")
            if result:
                items.append(json.loads(result))
            else:
                break

        if items:
            await process_batch(items)
        else:
            await asyncio.sleep(POLL_INTERVAL)
```

---

## 6. Error Handling & Recovery

### Queue Item Failure

```
On processing error:
  ├── Log error with UUID
  ├── RPUSH item back to queue (retry)
  ├── Increment retry counter in game state
  └── After 3 failures → move to dead letter queue
```

### Dead Letter Queue

```
games:queue:dead          → Failed items after 3 retries
games:{uuid}:errors       → Error log per game
```

### Stale Data Cleanup

```
Scheduled job (cron or at boot):
  ├── SCAN for games:{uuid}:state keys with TTL < now
  ├── Delete associated games:{uuid}:rag keys
  └── Log cleanup events
```

---

## 7. Redis Commands Summary

### Web Server (DB 0)
```python
RPUSH games:queue '{"uuid":"...","action":"..."}'
SELECT 1; EXISTS games:{uuid}:state      # check if game exists in DB 1
```

### AI Server (DB 0 → DB 1)
```python
LPOP games:queue                          # poll for work (non-blocking)
SELECT 1
SETNX games:{uuid}:lock "worker-1" NX EX 30  # acquire lock
HGETALL games:{uuid}:state               # load full state

# Patch only changed fields:
HSET games:{uuid}:state player '{...}'
HSET games:{uuid}:state monsters '[...]'
HSET games:{uuid}:state story "<gzip+base64>"
EXPIRE games:{uuid}:state 3600           # refresh TTL (1h sliding)
DEL games:{uuid}:lock                    # release lock

# Drain check (every 10 actions or major):
HDEL games:{uuid}:state story incidents  # clear drained fields
# split → embed → upsert to Upstash Vector:
# index.upsert(vectors=[("{uuid}:chunk:{i}", vec, meta)], namespace=uuid)
```

### Memory Ingestion (Upstash Vector)
```python
from upstash_vector import Index
index = Index(url=os.environ["UPSTASH_VECTOR_REST_URL"],
              token=os.environ["UPSTASH_VECTOR_REST_TOKEN"])

# write: on drain
index.upsert(vectors=[(f"{uuid}:chunk:{i}", vec, {"uuid": uuid,
               "chunk_index": i, "turn": turn, "text": chunk})
               for i, (chunk, vec) in enumerate(zip(chunks, embeddings))],
             namespace=uuid)

# read: node4_tool_agent memory retrieval
hits = index.query(vector=query_embedding, top_k=5,
                   include_metadata=True, namespace=uuid)

# cleanup: on game_over or 1h state expiry
index.delete(namespace=uuid)   # or: index.delete(ids=[...], namespace=uuid)
```

---

## 8. Memory Budget (Free Tier)

| Key Type | Count | Avg Size | Total |
|----------|-------|----------|-------|
| Queue items (DB 0) | ~50 | 200B | 10KB |
| Game states (DB 1) | ~20 | 15KB | 300KB |
| Coordination (locks, heartbeats, counters) | ~50 | 100B | 5KB |
| **Redis total** | | | **~315KB** |

**Upstash Vector (separate product, own free tier):**
| | Count | Size |
|--|-------|------|
| Vectors (384-dim × 4B float = 1.5KB each) | ~20 games × 50 chunks | ~1.5MB |
| Metadata (text, turn, is_incident) | same | ~2MB |
| **Total** | | **~3.5MB** (limit: 200M vectors×dims, 1GB) |

Redis free tier (256MB, 10k cmds/day) only carries queue + state — no vectors, no staging. Vector traffic (upserts + queries) is billed against Upstash Vector's own free tier (10k queries/day).

---

## 9. Master Implementation Checklist

### ─── DB 0 — Queue & Coordination (prefix `input:`) ───

**Redis key patterns:**
- `input:queue` — List for pending game requests
- `input:queue:delayed` — Sorted Set for retry with backoff
- `input:queue:dead` — Sorted Set for failed items (dead letter)
- `input:workers:{id}:heartbeat` — String TTL 15s

| Item | Project | Status |
|------|---------|--------|
| `input:queue` List — RPUSH (web) / LPOP (worker) non-blocking | rpg_ai_server | ✅ `InputRedisClient.pop_request/push_request` |
| `input:queue:delayed` Sorted Set — exponential backoff | rpg_ai_server | ✅ `InputRedisClient.push_delayed/pop_delayed_due` |
| `input:queue:dead` Sorted Set — max 3 retries then dead | rpg_ai_server | ✅ `InputRedisClient.push_dead` |
| Background mover — ZRANGEBYSCORE → RPUSH every 1s | rpg_ai_server | ✅ `QueueManager._mover_loop` |
| `workers:{id}:heartbeat` — SET with TTL 15s | rpg_ai_server | ✅ `InputRedisClient.set_heartbeat/get_heartbeat` |
| Queue item carries `retry_count` + `max_retries` | rpg_ai_server | ✅ `QueueManager.next_request/handle_failure` |
| Retry delay = 5 × 2^retry_count (5s, 10s, 20s, 40s) | rpg_ai_server | ✅ `backoff_delay()` in `redis/queue.py` |
| DLQ cleanup — ZREMRANGEBYSCORE older than 7d | rpg_ai_server | ⬜ Pending |
| Alert when DLQ > 100 items | rpg_ai_server | ⬜ Pending |

### ─── DB 1 — Game State (prefix `games:`) ───

**Redis key patterns:**
- `games:{uuid}:state` — Hash of game state fields
- `games:{uuid}:lock` — String, SETNX with TTL 30s
- `games:{uuid}:counter` — Integer, INCR per action, RESET on drain
- `games:{uuid}:coord:{x}_{y}` — Integer, coordinate→chunk index (future)

| Item | Project | Status |
|------|---------|--------|
| `games:{uuid}:state` Hash — HSET/HGET/HGETALL/HDEL | rpg_ai_server | ✅ `GamesRedisClient.hset/hget/hgetall/hdel` |
| `games:{uuid}:lock` — SETNX acquire + owner-checked release | rpg_ai_server | ✅ `GamesRedisClient.acquire_lock/release_lock/refresh_lock` |
| `games:{uuid}:counter` — INCR per action, RESET on drain | rpg_ai_server | ✅ `GamesRedisClient.incr/set_counter` |
| 1h sliding TTL — EXPIRE 3600 on every save | rpg_ai_server | ✅ `GameStateManager.save_state` |
| Patch-based writes — HSET only changed fields | rpg_ai_server | ✅ `GameStateManager.save_state` |
| Load existing state from Redis on request | rpg_ai_server | ✅ `GameStateManager.load_state` → `orchestrator.py` |
| Save initial state on first request | rpg_ai_server | ✅ `GameStateManager.save_initial_state` |
| SETNX lock acquired before LangGraph processing | rpg_ai_server | ✅ `orchestrator.py` |
| Lock released in `finally` block (30s auto-expire) | rpg_ai_server | ✅ `orchestrator.py` |
| Field-level dirty tracking (only HSET mutated fields) | rpg_ai_server | ⬜ Pending (H9 fix) |
| `version` field for optimistic locking | rpg_ai_server | ⬜ Pending (M4) |
| `status` field (`idle`/`processing`/`error`) | rpg_ai_server | ⬜ Pending (M5) |
| `games:{uuid}:coord:{x}_{y}` → chunk index mapping | rpg_ai_server | ⬜ Pending (M8, G3) |

### ─── Game Memory — Upstash Vector (replaces DB 2 rag staging) ───

**Removed:** `rag:queue` List, `rag:{uuid}:{idx}` Hash, `RagRedisClient`, DB 2 — no staging, no Chroma.

| Item | Project | Status |
|------|---------|--------|
| Drain trigger — counter ≥ 10 OR major action | rpg_ai_server | ✅ `GameStateManager.try_drain` |
| Compress story/incidents with gzip+base64 in state | rpg_ai_server | ✅ `compress_text()` in `utils/compression.py` |
| HDEL story/incidents from state after drain | rpg_ai_server | ✅ `GameStateManager.try_drain` |
| RESET counter to 0 after drain | rpg_ai_server | ✅ `GameStateManager.try_drain` |
| Major action keywords: death, level_up, quest_complete, boss_kill, new_biome | rpg_ai_server | ✅ Defined in `game_state.py` |
| `upstash-vector` dependency (`pip install upstash-vector`) | rpg_ai_server | ⬜ To add |
| `UPSTASH_VECTOR_REST_URL` / `UPSTASH_VECTOR_REST_TOKEN` env vars | rpg_ai_server | ⬜ To add |
| Embedding model — sentence-transformers `all-MiniLM-L6-v2` (384-dim) | rpg_ai_server | ⬜ To add |
| `split_into_chunks()` — 10k-token chunks on paragraph boundaries | rpg_ai_server | ⬜ To add |
| `index.upsert(vectors, namespace=uuid)` on drain | rpg_ai_server | ⬜ To add |
| `index.query(vector, top_k=5, include_metadata=True, namespace=uuid)` in node4 | rpg_ai_server | ⬜ To add |
| Inject `rag_context` into LLM prompt | rpg_ai_server | ⬜ To add |
| Content-hash check — skip upsert if story unchanged | rpg_ai_server | ⬜ Pending (H3) |
| Namespace cleanup on game_over / state expiry (`index.delete(namespace=uuid)`) | rpg_ai_server | ⬜ Pending |
| Retry with backoff on transient Vector API errors | rpg_ai_server | ⬜ Pending |
| Loop guards: router pass cap, RemainingSteps, recursion_limit=60, tool-call limit, futile-action guard | rpg_ai_server | ⬜ Pending — see `plan/loops.md` (L1–L10) |

### ─── Compression ───

| Item | Project | Status |
|------|---------|--------|
| `compress_text()` — gzip.compress + base64.b64encode | rpg_ai_server | ✅ `utils/compression.py` |
| `decompress_text()` — base64.b64decode + gzip.decompress | rpg_ai_server | ✅ `utils/compression.py` |
| Story compressed before HSET, decompressed after HGET | rpg_ai_server | ✅ Used in `game_state.py` |
| zstd as optional upgrade (better ratio/speed) | rpg_ai_server | ⬜ Future optimization |

### ─── Orchestrator & Wiring ───

| Item | Project | Status |
|------|---------|--------|
| `GameStateManager` wired into `GameOrchestrator` | rpg_ai_server | ✅ `orchestrator.py` |
| `QueueManager` handles retry on lock failure / exception | rpg_ai_server | ✅ `multi_tasker.py` + `queue.py` |
| `MultiTaskEngine` uses `QueueManager.next_request()` | rpg_ai_server | ✅ `multi_tasker.py` |
| ~~`RagCache` wrapper for DB 2 reads~~ — removed with DB 2 | rpg_ai_server | ⬜ Delete `redis/rag_cache.py` |
| ~~`RagRedisClient` created in `main.py`~~ — replaced by Vector client | rpg_ai_server | ⬜ Remove from `main.py` |
| ~~`.env.example` — `REDIS_RAG_DB`, `UPSTASH_REDIS_RAG_URL`, `UPSTASH_REDIS_RAG_TOKEN`~~ | rpg_ai_server | ⬜ Replace with `UPSTASH_VECTOR_REST_URL` / `UPSTASH_VECTOR_REST_TOKEN` |
| ~~`settings.py` — `rag_db`, `upstash_rag_url`, `upstash_rag_token`~~ | rpg_ai_server | ⬜ Replace with vector settings |
| `games:{uuid}:response` Hash + PUBLISH notify | rpg_ai_server | ⬜ Pending (H4, low priority) |
| Stale data cleanup — Lua script SCAN + TTL check + DEL (+ Vector namespace delete) | rpg_ai_server | ⬜ Pending (C7) |
| `GET /memory/export/{sid}` — full namespace dump via `index.range()` (Save & autosave) | rpg_ai_server | ⬜ Pending |
| `POST /memory/restore` — upsert locally saved chunks back into namespace | rpg_ai_server | ⬜ Pending |
| `EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"` | chroma-worker | ✅ Defined in plan |
| `EMBEDDING_DIM = 384` | chroma-worker | ✅ Defined in plan |
| `CHUNK_MAX_TOKENS = 10000` | chroma-worker | ✅ Defined in plan |

### ─── Plan Document Cleanup ───

| Item | Status |
|------|--------|
| Duplicate §3 → §4 renumber | ✅ Done |
| Schema B dangling deleted | ✅ Done |
| Architecture diagram fixed (arrows, 2-DB Redis + Upstash Vector) | ✅ Done |
| All `edit:` markers removed | ✅ Done |
| Chroma worker sections replaced with Upstash Vector ingestion | ✅ Done |
| Section 5 → LPOP drain-loop (was BRPOP hybrid) | ✅ Done |
| Memory budget recalculated (Redis 315KB, Vector ~3.5MB) | ✅ Done |
| Key naming convention updated for 2 DBs | ✅ Done |
| Implementation checklist comprehensive | ✅ This list |

---

## 10. Key Naming Convention

```
games:queue                     → Queue (DB 0) for pending requests
games:{uuid}:state              → Full game state Hash (DB 1)
games:{uuid}:lock               → Per-game processing lock (DB 1)
games:{uuid}:counter            → Action counter since last drain (DB 1)
games:queue:delayed             → Delayed retry queue (DB 0)
games:queue:dead                → Dead letter queue (DB 0)
workers:{id}:heartbeat          → Worker health check (DB 0)
```

**Upstash Vector (no Redis keys):**
```
namespace = {uuid}              → per-game memory scoping
id        = "{uuid}:chunk:{idx}"→ sequential chunk index
```

All keys use colon-separated namespaces. UUIDs are game session identifiers generated at game start.

---

## 11. Problems & Criteria

### CRITICAL Issues

#### C1 — Dual State Schema (Incompatible Formats)
The document contains **two completely different** game state JSON schemas (lines 105–258 vs 261–335) with no explanation, label, or deprecation note. They differ in:
- **Coordinate system**: Schema A uses 3D `{x, y, depth}`; Schema B uses 2D `{x, y}`
- **Entity identification**: Schema A uses `entity_id`; Schema B uses `name` as primary key
- **Player structure**: Schema A has survival stats, rune slots, weight limits, death count, biome history; Schema B has D&D stats, mana, class, flat 0–100 skills
- **Monster model**: Schema A has behavior/senses/targeting AI; Schema B uses level/aggro range
- **World model**: Schema A includes `current_chunk` (3×3 grid with blocks) and `buildings`; Schema B has neither

**Criteria**: Must pick **one** canonical schema. Delete or move the other to an appendix as an earlier draft.

**Fix Plan**: there is Depth parameter only so actually grid is just 2d actually with depth to treat ir as z coordinate so it's 3d in 2d space. and current block only so it be memory efficient.

#### C2 — At-Most-Once Delivery Accepted (RPUSH/LPOP)
`BRPOP` atomically removes the queue item **before** processing (original design). If the AI server crashes between LPOP and HSET, the item is permanently lost. This is **accepted** — at-most-once is fine because:
- Critical data (player state) is already persisted from the previous action
- One lost action is recoverable by the player re-sending
- RPUSH/LPOP preserves FIFO ordering with zero complexity
- Simple LPOP (non-blocking with sleep fallback) avoids blocking issues

**Fix Plan**: Use **RPUSH** (web server) + **LPOP** (AI worker). Non-blocking, simple, no dependencies. RPUSH+LPOP preserves FIFO ordering — actions processed in the order they were sent. At-most-once risk acknowledged and accepted.

#### C3 — No Concurrency Control (Lost Updates)
Two workers can process actions for the same game UUID simultaneously (lines 416–491): both `HGET` the same state, modify independently, then `HSET` — **last writer wins**. No WATCH/MULTI/EXEC, no optimistic locking, no distributed lock (`SETNX`), no version field.

**Criteria**: Must add per-game locking (`SETNX games:{uuid}:lock` with TTL) or optimistic concurrency with version checks.

**Fix Plan**: Use **SETNX per-game distributed lock** with TTL + heartbeat. `SET games:{uuid}:lock {worker_id} NX EX 30` before processing. Worker extends lock every 10s via `EXPIRE` during long LLM calls. Release via Lua script (`GET` → check owner → `DEL`). Background reclaim scans for stale locks (lock exists but worker heartbeat absent). This is preferred over WATCH/MULTI because AI processing takes seconds (LLM calls), making optimistic retries prohibitively expensive.

#### C4 — RAG Key Pattern: Hash vs Multiple Keys Ambiguity
Line 42 defines `games:{uuid}:rag` as a **Hash**, and line 640 uses `HSET` on it. But line 68 uses glob `games:{uuid}:rag:*` (implying **multiple keys**). If it's one Hash, `EXPIRE` at line 641 expires the **entire hash** — all chunks disappear simultaneously. If it's separate keys, the HSET command is wrong.

**Criteria**: Decide single Hash vs separate key-per-chunk. If separate keys, each gets independent TTL. If single Hash, document that all memory expires together.

**Fix Plan**: **Superseded** — memory left Redis entirely. Chunks are now vectors in Upstash Vector (id `{uuid}:chunk:{idx}`, namespace `{uuid}`), so Redis TTL/expiry questions no longer apply. What gets remembered is **incidents and story**, not the world (the world is a static map — no need to make memory for it). On each major incident/story drain, the drained text is embedded and upserted, then removed from `story`/`incidents` fields — the index always holds everything searchable.

#### C5 — `chunk_5` Is Undefined
Legacy issue about `chunk_5_story` / `chunk_5_incidents` naming (previously lines 344–354, 640). No mapping function from chunk coordinates to RAG key suffix was defined.

**Criteria**: Define a deterministic chunk key scheme so the ingester and retriever agree on chunk identity.

**Fix Plan**: Use **sequential chunk index** (0, 1, 2...) as the vector id suffix in Upstash Vector: `"{uuid}:chunk:{idx}"`, coordinate/turn stored in metadata, not baked into id. `split_into_chunks()` is used once (AI server side, at drain).

#### C6 — No Vector Store in Redis (Upstash Vector instead of Chroma)
Legacy: "RAG retrieval is handled by Chroma DB on a separate server, Redis DB 2 only stages compressed text."

**Fix Plan**: **Superseded by Upstash Vector.** Redis does zero vector operations. Embeddings and similarity search live in Upstash Vector (dense cosine index, namespace per session). The AI server embeds and upserts directly at drain time — no staging queue, no Chroma, no `FT.CREATE` anywhere.

#### C7 — Stale Data Cleanup Logic Is Broken
Line 606: `SCAN for games:{uuid}:state keys with TTL < now`. `TTL` returns **seconds remaining** (e.g., 36000), not a Unix timestamp. Comparing `36000 < 1718800000` is always true (deletes everything) or `36000 < 30` is always false (deletes nothing). This is mathematically nonsensical.

**Criteria**: Use `TTL < threshold_seconds` (e.g., `TTL < 60` means "expiring within 60 seconds") or check `OBJECT IDLETIME`.

**Fix Plan**: Write Lua script: `SCAN 0 MATCH games:*:state COUNT 100` → for each key, `TTL key` → if `TTL >= 0 AND TTL < 60`, extract UUID, `DEL games:{uuid}:state games:{uuid}:lock` + `index.delete(namespace=uuid)` (Upstash Vector cleanup). Runs atomically — no race between TTL check and DELETE. Run via cron every 5–10 min. Alternative: use `OBJECT IDLETIME` for LRU-style eviction of keys untouched for >24h.

### HIGH Severity Issues

#### H1 — Duplicate Section Number "3"
Sections "Base64 Encoding" (line 359) and "Data Flow" (line 400) are both labeled **§3**. All subsequent sections (4–10) are off by one from the author's intent.

**Criteria**: Renumber sections 3–10 sequentially.

**Fix Plan**: Renumber: "3. Base64 Encoding" stays §3 (now "String Compression Strategy"). "3. Data Flow" → "4. Data Flow". Delete old redundant "4. Base64 Encoding Strategy" (now empty — merged into §3). Sections 5–10 keep their numbers. See C1 also removes Schema B text which shifts line numbers.

#### H2 — Section 4 Now Empty (Was Base64 Redundancy)
"Base64 Encoding Strategy" was deleted — it repeated §3 with only a Python snippet. The snippet is now in §3's Implementation block.

**Criteria**: Already resolved — section 4 was deleted. No further action.

**Fix Plan**: Already done — section 4 deleted, Python snippet merged into §3.

#### H3 — Unconditional Embedding on Every Action
Legacy: AI server pushed to `rag:queue` on every action; Chroma worker re-embedded identical data.

**Criteria**: Only embed when story or incidents actually changed. Use a content-hash check or dirty flag.

**Fix Plan**: Compute `sha256(story + incidents)` and compare to a stored hash; skip upsert if unchanged. Store hash as `games:{uuid}:state` field `content_hash`. Drain already limits embedding to every 10 actions or major action — never per-action.

#### H4 — No Response/Notification to Web Server
Web server receives `202 Accepted` (line 408) but has no way to learn the outcome — no result queue, no pub/sub channel, no webhook. The diagram shows "reads response" with `GET` (line 20) but no response key pattern is defined.

**Criteria**: Define a `games:{uuid}:response` key or use pub/sub to notify the web server when processing completes.

**Fix Plan**: Web server pre-creates `games:{uuid}:response` Hash with `status=pending` before enqueueing. AI server writes `status=success` + `story` + `incidents` + `summary` + `version` after Phase 4, then `PUBLISH games:{uuid}:notify {response_id}`. Web server subscribes for real-time notification (or polls with timeout fallback). `EXPIRE games:{uuid}:response 60`. Architecture diagram: replace vague `GET` arrow with "reads `games:{uuid}:response`".

#### H5 — Orphaned Memory After State Expiry
Legacy: state TTL 24h vs RAG TTL 7d left orphaned RAG for days.

**Criteria**: Memory must not outlive an abandoned session.

**Fix Plan**: Upstash Vector namespaces have no TTL — cleanup is explicit: LangGraph cleanup node deletes the namespace when `state.game_over == True` (`index.delete(namespace=uuid)`), and the stale-data cleanup (C7) does the same when state TTL expires. On exit, the player keeps the memory locally (`localStorage["rpg:memory:{id}"]`, scenario registry) — on entry, expired sessions are restored from that blob via `POST /memory/restore`. Server does not persist beyond 1h sliding window.
#### H6 — EXPIRE on RAG Hash Expires Everything Together
Legacy: `EXPIRE games:{uuid}:rag 604800` on a Hash gave all chunks one shared clock.

**Criteria**: Chunks/vectors must not share expiry.

**Fix Plan**: **Superseded** — no RAG keys in Redis. Each vector is independent in Upstash Vector; deletion is by namespace or by id. No TTL bookkeeping needed.

#### H7 — Compression: Use gzip/zstd Instead of Raw Text
Story/incidents are the largest fields in the state Hash. Storing them as raw JSON strings wastes Redis memory. Narrative text compresses extremely well (60-80% reduction with gzip/zstd).

**Criteria**: Compress story/incidents with gzip (or zstd) before storing. Decompress on read. Store compressed bytes as base64 string in Redis Hash.

**Fix Plan**: Use `gzip.compress(text.encode("utf-8"))` → `base64.b64encode()` before HSET. Reverse on HGET. Python's built-in `gzip` module requires no dependencies. For better performance, use `pyzstd` (Zstandard). Size comparison for 80KB story: raw=80KB, gzip+base64=~24KB (70% reduction).
#### H8 — Memory Budget Underestimates
- **State size**: Estimated 5KB. Realistic: 15–30KB (player + allies + monsters + 9 chunks of blocks with physics + buildings)
- **Vector size**: A 384-dim embedding is ~1.5KB; with text + metadata JSON, 2.5–4KB per chunk. 768-dim models double that.

**Criteria**: Recalculate with realistic per-state sizes, include Redis overhead (30–50%), and model worst-case growth.

**Fix Plan**: Two budgets:
- **Redis** (queue + state only): Low 10 games ~3MB, Medium 50 games ~15MB, High 200 games ~60MB. `maxmemory-policy allkeys-lru` + runtime `INFO memory` check at 90%.
- **Upstash Vector** (embeddings + metadata, free tier 200M vectors×dims / 1GB): a game session with ~200 chunks × 3KB ≈ 600KB; 100 concurrent sessions ≈ 60MB — far inside the free limit. Namespace cleanup on game over keeps it bounded.

#### H9 — No Field-Level Change Detection
The plan says "only patch what changed" (lines 478–484) but provides no diff logic, dirty-bit tracking, or change detection. If the AI server writes back all fields naively, patching is no better than full SET.

**Criteria**: Implement explicit dirty tracking. Only HSET fields that actually mutated.

**Fix Plan**: Add in-memory `dirty = set()` per processing cycle. On each state mutation, `dirty.add(field_name)`. On flush, `HSET` only dirty fields, then `dirty.clear()`. Track content hash per chunk to detect story/incidents changes: `sha256(chunk_text)` → skip re-embedding if unchanged.

#### H10 — No TTL on Dead Letter Queue
`games:queue:dead` (line 598) has no TTL and is not listed in the TTL table (lines 64–69). Failed items accumulate unbounded.

**Criteria**: Add 7-day TTL to dead letter queue items.

**Fix Plan**: Replace `RPUSH games:queue:dead` with `ZADD games:queue:dead {score=timestamp} {item}`. Periodic `ZREMRANGEBYSCORE games:queue:dead -inf {now-7d}` cleanup. Items carry full retry history for debugging. Add alerting when DLQ grows beyond threshold (e.g., >100 items).

### MEDIUM Severity Issues

| # | Issue | Lines | Criteria | Fix Plan |
|---|-------|-------|----------|----------|
| M1 | Retry counter stored in state (24h TTL) — if processing spans >24h, counter resets, causing infinite retry loop | 587–593 | Store retry count on the queue item itself | Move `retry_count` and `max_retries` into queue item JSON. Error handler increments on item, not state. Item survives state TTL expiry. |
| M2 | No exponential backoff on retry — items re-queued immediately, burn Redis commands | 587–593 | Add `retry_delay` field, use `ZADD` with score=time+delay instead of `RPUSH` | Replace `RPUSH` with `ZADD games:queue:delayed {score=now+delay}`. Delay = `5 × 2^retry_count` (5, 10, 20, 40s). Background mover coroutine transfers due items back to main stream every 1s. |
| M3 | Embed payload lacked chunk context — ingester had to re-read full state | 491 | Include `chunk_index` in the built metadata | Vector metadata carries `{uuid, chunk_index, turn, is_incident}` — the upsert payload IS the chunk context. No re-reads. |
| M4 | No `updated_at` / `version` field on game state — impossible to implement optimistic locking | 103–258 | Add `version` (integer, incremented on each write) | Add `version` field to state Hash. Increment on every HSET batch. Include in response Hash. Future: use WATCH on version for optimistic CAS. |
| M5 | No `status` field on game state — can't detect double-processing or stale locks | 103–258 | Add `status` field: `idle` / `processing` | Add `status` to state Hash: `"idle" → "processing" → "idle" | "error"`. Check before lock acquisition: if `status == "processing"`, re-queue with backoff instead of processing in parallel. |
| M6 | Coordinated cleanup races with active sessions — SCAN may delete memory for a session that just refreshed its state | 603–609 | Use Lua script for atomic TTL-check-and-delete + namespace delete | Same Lua script as C7: SCAN → TTL check → also check lock TTL. Only delete if lock is absent/expired (session not active). All operations atomic within EVAL, then `index.delete(namespace=uuid)`. |
| M7 | Schema B exists as dangling code block after Schema A — no fence, no heading, no purpose stated | 261–335 | Remove or label clearly | Resolved by C1 — delete lines 260–336 entirely. Schema A is canonical. |
| M8 | Chunk coordinate vs chunk key in RAG — no function maps `{x, y}` to RAG field name | 344, 640 | Define deterministic chunk identity | Vector id = `"{uuid}:chunk:{idx}"` (sequential index). Coordinates/turn are metadata, not ids. No coord→index mapping needed. |
| M9 | Queue item has no `retry_count` — yet retry logic says "increment retry counter in game state" | 93–99, 591 | Add `retry_count` to queue item JSON | Add `retry_count: 0` and `max_retries: 3` to queue item on enqueue. Error handler increments on item, sends to DLQ when exhausted. |
| M10 | Count-based polling describes batch BRPOP but BRPOP is single-item — hybrid is just time-based with join | 552–556 | Rename "batch" to "time-based with drain loop" | Rename strategies: "Time-based" → "Fixed-interval", "Count-based" → remove (misleading), "Hybrid" → "Drain-loop". Rename `BATCH_SIZE` → `DRAIN_LIMIT`. |
| M11 | No worker heartbeat / health check — no way to detect dead workers with claimed items | absent | Add heartbeat key per worker with short TTL | `workers:{worker_id}:heartbeat` with TTL 15s, updated every 5s. Include current game UUID. Background reclaim checks lock owners against heartbeat — stale locks from dead workers get DEL'd. |
| M12 | No concurrency model in memory budget — assumes 20 simultaneous games, queue depth of 50 | 648–656 | Add concurrency multiplier and burst projection | Add multipliers: queue-buffer (2×), lock/overhead (1.5×), burst-peak (3×). Budget formula: `base × 2 × 1.5 × 3 = 9× base`. With 50 games at 106MB base: burst peak = ~954MB. Add `maxmemory-policy allkeys-lru`.

### UNCLEAR / AMBIGUOUS — Resolved

| # | Question | Resolution |
|---|----------|------------|
| U1 | What does `chunk_5` mean? | Placeholder. Now: sequential `chunk_index` (0, 1, 2...) as vector id suffix `"{uuid}:chunk:{idx}"`. |
| U2 | Hash vs multiple keys for RAG? | **Superseded** — no RAG keys in Redis. One Upstash Vector namespace per game, one vector per chunk. |
| U3 | How does web server read response? | New `games:{uuid}:response` Hash written by AI server. `PUBLISH games:{uuid}:notify` for real-time notification. Web server polls or subscribes. |
| U4 | Is Schema B an older draft? | Yes — earlier draft with 2D coords, D&D stats, no world model. Delete (see C1 fix). |
| U5 | Chunk mapping on player move? | Chunks are narrative, not spatial. Each drain appends new vectors with `{turn, chunk_index}` metadata; retrieval is similarity-based, not spatial. |
| U6 | Embedding model / dimensions? | **384-dim `all-MiniLM-L6-v2`** (sentence-transformers). Config setting: `EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"`, `DIM=384`. |
| U7 | "Batch" in batch processing? | Misleading name. Renamed to "Drain-loop" — poll once, then drain up to N items via non-blocking pops. |

---

## 12. Agentic AI Integration with Memory (Upstash Vector)

### Overview

Semantic game memory lives in **Upstash Vector** — a dense cosine index, one namespace per session (`{uuid}`). The AI server embeds and upserts at drain time (no Chroma, no staging queue, no external worker).

### Architecture

```
Player Action → LangGraph Pipeline
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
node5_context   node4_tool_agent   node6_story_generator
  injection     (Vector query)     (LLM produces text)
                                     │
                                     ▼
                               node7_output_pusher
                                     │
                          ┌──────────┴──────────┐
                          ▼                     ▼
                   decompress story       detect drain trigger
                   (gzip → text)          (10 actions OR major)
                          │                     │
                          └──────────┬──────────┘
                                     ▼
                          split → embed → upsert
                          Upstash Vector, namespace={uuid}
                                     │
                                     ▼
                          node4_tool_agent
                          (index.query → rag_context)
```

### Chunk Splitting & Embedding (AI Server Side)

```python
import gzip, base64

CHUNK_MAX_TOKENS = 10000
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

def estimate_tokens(text: str) -> int:
    return len(text) // 4

def split_into_chunks(text: str, max_tokens: int = CHUNK_MAX_TOKENS) -> list[str]:
    if estimate_tokens(text) <= max_tokens:
        return [text]
    chunks, current, current_tokens = [], [], 0
    for p in text.split("\n\n"):
        pt = estimate_tokens(p)
        if current_tokens + pt > max_tokens and current:
            chunks.append("\n\n".join(current))
            current, current_tokens = [p], pt
        else:
            current.append(p)
            current_tokens += pt
    if current:
        chunks.append("\n\n".join(current))
    return chunks

def compress_text(text: str) -> str:
    compressed = gzip.compress(text.encode("utf-8"), compresslevel=6)
    return base64.b64encode(compressed).decode("ascii")

def decompress_text(encoded: str) -> str:
    compressed = base64.b64decode(encoded)
    return gzip.decompress(compressed).decode("utf-8")
```

### Memory Write Flow (on drain)

```python
from upstash_vector import Index
from sentence_transformers import SentenceTransformer

index = Index(url=os.environ["UPSTASH_VECTOR_REST_URL"],
              token=os.environ["UPSTASH_VECTOR_REST_TOKEN"])
model = SentenceTransformer(EMBEDDING_MODEL)  # loaded once at boot

async def drain_to_memory(uuid: str, story_gz: str, incidents_gz: str, turn: int):
    text = decompress_text(story_gz) + "\n\n" + decompress_text(incidents_gz)
    chunks = split_into_chunks(text)
    vectors = model.encode(chunks).tolist()          # list[list[float]] 384-dim
    index.upsert(
        vectors=[
            (f"{uuid}:chunk:{i}", vectors[i],
             {"uuid": uuid, "chunk_index": i, "turn": turn, "text": chunks[i]})
            for i in range(len(chunks))
        ],
        namespace=uuid,
    )
```

### Agentic AI Memory Retrieval Flow (via Upstash Vector)

```
node4_tool_agent (enriched with memory from Upstash Vector):
  │
  ├── 1. Build query from current context:
  │       query_text = f"Location: {loc}. Recent events: {events[:5]}. Active: {quests}"
  │
  ├── 2. Embed query with the SAME model (384-dim)
  │
  ├── 3. Query Upstash Vector:
  │       hits = index.query(vector=q_vec, top_k=5,
  │                          include_metadata=True, namespace=uuid)
  │
  ├── 4. Inject into LangGraph state:
  │       state.rag_context = "\n---\n".join(h["metadata"]["text"] for h in hits)
  │       # ~2000 chars of relevant past memory
  │
  ├── 5. Tools execute with RAG context available
  │
  └── 6. LLM prompt now includes:
        "PREVIOUS MEMORIES: {rag_context}"
        → Coherent narrative that references past events
```

### Memory Lifecycle

| Turn | Action | Memory State | Agent Memory |
|------|--------|--------------|--------------|
| 1 | Player enters forest | Vector ns: chunk 0 "entered dark forest" | — |
| 2 | Fights goblins | Story drains (10 actions), Vector ns: chunk 1 "fought 3 goblins" | query → chunk 0 context |
| 3 | Travels to cave | Story drains, Vector ns: chunk 2 "arrived at cave" | query → "You remember the goblin fight" |
| 10 | Autosave (every 10 msgs) | drain fires → client exports ns → `localStorage["rpg:memory:{id}"]` refreshed | — |
| 1h idle | — | Redis state TTL expires | Vectors persist (no TTL) |
| Exit (player leaves) | client saves (export) or discards (optional `index.delete(namespace)`) | namespace intact while unsaved | client-driven, see fullstack folder |
| Resume / new entry | restore saved chunks via `/memory/restore`, or fresh namespace | memory works from turn 1 | client-driven, see fullstack folder |
| game over | cleanup node | `index.delete(namespace=uuid)` | gone |

**Scenario lifecycle note (server side):** a scenario = user-chosen name (client label) + uuid (Upstash Vector namespace, `{uuid}` so renames never touch vectors). Exit never destroys vectors — only `game_over`, stale sweep, or explicit "Don't save → delete". Autosave piggybacks the existing `counter ≥ 10` drain (sets an `autosave` flag in drained state). Client flows (registry, popups) are owned by the fullstack folder. Full contract: `REDIS_API.md` → "Scenario Lifecycle".

### Key Properties

- **Managed vector store**: Upstash Vector handles indexing + similarity search (no self-hosted Chroma, no worker service to run)
- **Per-game scoping**: namespace per UUID (up to 100 namespaces on free tier)
- **Compressed in Redis**: story/incidents stay gzip-compressed in state; decompressed only at drain
- **Deterministic chunking**: `split_into_chunks()` used once, in the AI server
- **No Redis vector ops**: zero FT.SEARCH, zero embeddings stored in Redis
- **Same embedding model** for write and query (`all-MiniLM-L6-v2`, 384-dim) — mismatch silently degrades recall

---

## 13. Validation Findings (Post-Edit Audit)

### CONTRADICTIONS — All Resolved

| # | Conflict | Status | Resolution |
|---|----------|--------|------------|
| ~~V1~~ | ~~C4 drain vs §12 accumulate~~ | **RESOLVED** | §12 rewritten for Upstash Vector. Story/incidents drain from DB 1 → embedded → upserted to Vector namespace. No Redis staging. |
| ~~V2~~ | ~~H5 1h TTL vs TTL table~~ | **RESOLVED** | Redis TTLs at 1h sliding. Vector namespaces have no TTL — cleaned explicitly on game over / stale cleanup. |
| ~~V3~~ | ~~Base64 vs §12~~ | **RESOLVED** | Compression section finalized (gzip+base64 for Redis storage). |
| ~~V4~~ | ~~C6 no vector index vs FT.SEARCH~~ | **RESOLVED** | No FT.SEARCH anywhere. Upstash Vector handles all vector operations. Redis does zero vector ops. |
| ~~V5~~ | ~~H4 no response vs diagram~~ | **RESOLVED** | Architecture diagram updated. No response channel — 202 is final. Polling or SSE TBD later. |

### PERFORMANCE CLAIMS — Audit Results

| # | Claim | Verdict | Analysis |
|---|-------|---------|----------|
| P1 | **H7: Compression with gzip/zstd** | **CORRECT** | gzip compresses narrative text 60-80%. With base64 wrapper (+33%), net reduction is still 60-80%. zstd at level 3 achieves 65-85% reduction with faster decompression. Recommended approach. |
| P2 | **Embedding cost at drain** | **CORRECT** | 10k-token chunks → ~20 chunks × 384-dim per drain. sentence-transformers batches this in one call (<1s on CPU for 20 short chunks). The 10-action drain window keeps total embedding calls ~90% lower than per-action. |
| P3 | **H3: Batch embed every 10 actions** | **CORRECT** | ~90% reduction in embedding runs vs per-action. 20 chunks per batch max. Un-embedded window of 9 actions is acceptable — story stays in state for working memory. |
| P4 | **H5: 1h TTL + client cache** | **PROBLEMATIC** | Introduces split-brain (client cache vs Redis) and data loss risk (0-59min window). See G5 for full analysis. |
| P5 | **H8: Only 3×3 chunks in Redis** | **Already correct** | Original design (line 103) already states "center + 8 surrounding = 3×3 grid." No change needed. |

### GAPS — Updated for New Architecture

| # | Gap | Owner | Status | Suggestion |
|---|-----|-------|--------|------------|
| G1 | **No drain node defined** | C4 | **DONE** | `GameStateManager.try_drain()` in `redis/game_state.py`. Checks counter ≥ 10 or major action. HDELs story/incidents from DB 1 and triggers embed+upsert to Vector. |
| G2 | **Ingestion ownership** | C4 + §12 | **DONE** | In-process: AI server splits, embeds, upserts at drain. No external worker. |
| G3 | **"Major action" undefined** | C4 + H3 | **HIGH** | Define list: `DEATH`, `LEVEL_UP`, `QUEST_COMPLETE`, `BOSS_KILL`, `NEW_BIOME`. LLM sets `is_major: true` flag. |
| G4 | **No response path for web server** | H4 | **LOW** | Accepted. 202 is final. User polls or SSE endpoint added later. |
| ~~G5~~ | ~~Client cache undefined~~ | H5 | **RESOLVED** | Cache removed. 1h server-only TTL with sliding window — no client-side complexity. |
| G6 | **Decompression in pipeline** | H7 + §12 | **DONE** | `decompress_text()` available in `utils/compression.py`. Compression applied in save/load paths. |
| G7 | **No action counter mechanism** | H3 | **DONE** | `INCR games:{uuid}:counter` via `GamesRedisClient.incr()`. Reset on drain via `set_counter()`. Threshold = 10. |
| G8 | **Namespace management** | §12 | **MEDIUM** | Namespace = `{scenario uuid}` (name is a client label). Cleanup on game over (`index.delete(namespace=uuid)`), stale-state sweep (C7), or "Don't save" exit; "Save" exit keeps the namespace for resume via `/memory/restore`. |
| G9 | **Old key structure references** | §2 | **DONE** | Already updated to 2 DBs + Vector. |
| G10 | **Commands summary outdated** | All | **DONE** | Already updated for RPUSH/LPOP, 2 DBs, Vector upsert/query. |
| G11 | **Implementation checklist missing items** | All | **DONE** | Checklist updated with all implemented items + new Vector items. |

### RECOMMENDED RESOLUTIONS — Applied

All contradictions resolved via debate decisions:
- **RPUSH/LPOP** for queue (no Streams, at-most-once accepted)
- **SETNX lock** for concurrency (100-200ms < re-running LangGraph)
- **Upstash Vector** for memory (no Chroma, no DB 2 staging — managed vector store)
- **1h sliding TTL** with session extension on every action (no client cache)
- **Drain pattern**: story/incidents → split → embed → upsert to Vector on major event or every 10 actions
- **No response channel**: 202 Accepted is final, SSE/polling added later
- **gzip+base64**: compress before storing, decompress on read, 60-80% reduction
