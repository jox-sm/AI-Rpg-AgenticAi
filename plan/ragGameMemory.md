# RAG Game Memory

## Architecture
2 Railway services, 3 Upstash Redis databases.

```
┌──────────────────────┐                ┌──────────────────────────┐
│  Game Server         │                │  Embedding Server        │
│  (Railway)           │                │  (Railway)               │
│                      │                │                          │
│  - LLM calls         │                │  - sentence-transformers │
│  - game logic        │                │    (loaded once)         │
│  - items DB          │                │                          │
│                      │                │  BRPOP embed:queue       │
│                      │                │  embed → RPUSH result    │
└──────┬───────────────┘                └──────────┬───────────────┘
       │                                           │
       │            ┌──────────────────┐           │
       │            │    Upstash       │           │
       ├───────────►│    Redis         │◄──────────┤
       │            │                  │           │
       
       │   DB 0:    │   game:data:*    │           │
       │   Static   │   items/names    │           │
       │   game     │   characters     │           │
       │   data     │   maps/tags      │           │
       │            │   descriptions   │           │
       │            │   images         │           │
       │            │   Hot-games      │           │
       │            │                  │           │
       │   DB 1:    │   session:*      │           │
       │   Active   │   user→game      │           │
       │   sessions │   current_state  │           │
       │            │   turn_number    │           │
       │            │                  │           │
       │   DB 2:    │   memory:*       │           │
       │   Per-user │   events         │           │
       │   memory   │   embeddings     │           │
       │            │   incidents      │           │
       └───────────►│                  │◄──────────┘
                    └──────────────────┘
```

---

## 3 databases

### DB 0: Static game data (reference)
Loaded once at boot, rarely written.

```
game:data:items:{id}       → {"name": "Iron Sword", "type": "weapon", ...}
game:data:characters:{id}  → {"name": "Alderman Thorne", "faction": ...}
game:data:maps:{id}        → {"biome": "forest", "size": "15x15", ...}
game:data:tags:{tag}       → ["item1", "item2", ...]
```

Populated by the items-db parser + manual seeding. Read-only during gameplay.

### DB 1: Active sessions
Per-game runtime state, sent to user for local caching when game ends.

```
session:{uuid}:user          → "user_abc123"
session:{uuid}:game_data     → {current_location, quest_status, ...}
session:{uuid}:turn          → 42
session:{uuid}:context_size  → 3200
session:{uuid}:rag_active    → "1"
```

### DB 2: Per-user memory
The RAG layer. Each user's game history + embeddings.

```
memory:{uuid}:events         → List of event strings (raw)
memory:{uuid}:embeddings     → List of {text, vector[384], turn}
memory:{uuid}:incidents      → List of significant incidents (filtered events)
memory:{uuid}:rag_active     → "1" after trigger
manage:embed:queue           → Shared queue for embedding work
```

---

## Key differences between DBs

| | DB 0 (Data) | DB 1 (Sessions) | DB 2 (Memory) |
|---|---|---|---|
| Volatile | No | Yes | Semi (per game) |
| Written by | You (setup) | Game server | Embed server |
| Read by | Game server | Game server | Game server |
| Lifetime | Forever | Until game ends | Until game ends |
| Size | Fixed (~10k keys) | ~100 keys/game | ~500 keys/game |

---

## Upstash setup

3 separate Upstash instances (each has its own free tier):

| Instance | Free tier | Used for |
|----------|-----------|----------|
| `rpg-data` | 10k cmds/day, 256MB | DB 0 (game data) |
| `rpg-sessions` | 10k cmds/day, 256MB | DB 1 (active sessions) |
| `rpg-memory` | 10k cmds/day, 256MB | DB 2 (per-user memory) |

Each gets its own `UPSTASH_REDIS_URL` in Railway env vars.

Or one instance with key prefixing (`data:*`, `session:*`, `memory:*`) it works same logic.

---

## Embedding server flow

```python
r_data = Redis(url=env["UPSTASH_DATA"])
r_session = Redis(url=env["UPSTASH_SESSIONS"])
r_memory = Redis(url=env["UPSTASH_MEMORY"])

model = SentenceTransformer("all-MiniLM-L6-v2")

while True:
    _, game_uuid = r_memory.brpop("manage:embed:queue")
    events = r_memory.lrange(f"memory:{game_uuid}:events", 0, -1)
    for event_text in events:
        vec = model.encode(event_text).tolist()
        chunk = json.dumps({"text": event_text, "vector": vec, "ts": time.time()})
        r_memory.rpush(f"memory:{game_uuid}:embeddings", chunk)
    r_memory.delete(f"memory:{game_uuid}:events")
```

---

## Free tier

| Component | Cost |
|-----------|------|
| Game Server (Railway) | Free credits |
| Embed Server (Railway) | Free credits (worker) |
| 3x Upstash Redis (free tier) | $0 |
| sentence-transformers | $0 (local) |
| **Total** | **$0/month** |
