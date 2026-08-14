# Game Memory (Upstash Vector)

## Architecture
2 Upstash services: **Upstash Redis** (queue + state) and **Upstash Vector** (per-game semantic memory). No Chroma, no embedding server, no RAG staging in Redis.

```
┌──────────────────────┐                ┌──────────────────────────┐
│  Game Server         │                │  Upstash Vector          │
│  (FastAPI/LangGraph) │                │  (managed vector store)  │
│                      │                │                          │
│  - LLM calls         │                │  Dense index, 384-dim    │
│  - game logic        │                │  COSINE similarity       │
│  - items DB          │                │  namespace = {uuid}      │
│                      │                │                          │
│  split → embed →     │  upsert        │                          │
│  query ──────────────┼───────────────►│  index.upsert(...)       │
│                      │◄───────────────┤  index.query(top_k=5)    │
└──────┬───────────────┘                └──────────────────────────┘
       │
       │            ┌──────────────────┐
       ├───────────►│    Upstash Redis │
       │            │                  │
       │   DB 0:    │   input:queue    │
       │   Queue    │   workers:heartbeat
       │            │                  │
       │   DB 1:    │   games:{uuid}:state (player, story gzip,
       │   State    │     incidents gzip, context_summary)
       │            │   output:{uuid}
       └───────────►│                  │
                    └──────────────────┘
```

---

## Why Upstash Vector (not Redis lists / not Chroma)

| Approach | Verdict |
|----------|---------|
| Brute-force cosine in Redis lists (old `memory:*` plan) | ❌ Moves ~1.5KB/vector through Redis, no indexing, O(n) scans in app code |
| Chroma DB (external worker + DB 2 staging) | ❌ Second external DB with its own uptime/billing, extra worker to run |
| **Upstash Vector (this plan)** | ✅ Managed, same Upstash auth model, namespaces for per-game scoping, free tier 200M vectors×dims + 10k queries/day |

---

## Setup (Upstash console)

Create one **Vector index** in the Upstash console (https://console.upstash.com/vector):

| Setting | Value |
|---------|-------|
| Type | **Dense** |
| Dimension | **384** (matches `all-MiniLM-L6-v2`) |
| Distance metric | **Cosine** |
| Plan | Free tier |

Grab `UPSTASH_VECTOR_REST_URL` and `UPSTASH_VECTOR_REST_TOKEN` from the index page.

### Env vars

```
UPSTASH_VECTOR_REST_URL=...
UPSTASH_VECTOR_REST_TOKEN=...
VECTOR_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_EMBEDDING_DIM=384
VECTOR_TOP_K=5
VECTOR_CHUNK_MAX_TOKENS=10000
```

---

## Memory layout (Upstash Vector)

```
namespace = {uuid}                 per-scenario scoping (up to 100 namespaces free)
id        = "{uuid}:chunk:{idx}"   sequential chunk index
metadata  = { uuid, chunk_index, turn, ts, is_incident, text }
```

The `uuid` is the **scenario id** — the user-chosen name is a client label (rename-safe). New scenario = new uuid = new namespace. The client-side registry (`rpg:scenarios`) is owned by the fullstack folder.

### Write — on drain (every 10 actions OR major event)

Major events: `death`, `level_up`, `quest_complete`, `boss_kill`, `new_biome`.

```python
from upstash_vector import Index
from sentence_transformers import SentenceTransformer

index = Index(url=os.environ["UPSTASH_VECTOR_REST_URL"],
              token=os.environ["UPSTASH_VECTOR_REST_TOKEN"])
model = SentenceTransformer(os.environ["VECTOR_EMBEDDING_MODEL"])  # loaded once

def drain_to_memory(uuid: str, story: str, incidents: str, turn: int):
    text = story + "\n\n" + incidents
    chunks = split_into_chunks(text)                       # 10k-token chunks
    vectors = model.encode(chunks).tolist()                # [384] each
    index.upsert(
        vectors=[
            (f"{uuid}:chunk:{i}", vectors[i],
             {"uuid": uuid, "chunk_index": i, "turn": turn, "text": chunks[i]})
            for i in range(len(chunks))
        ],
        namespace=uuid,
    )
```

### Read — per turn (node4_tool_agent)

```python
query_embedding = model.encode(
    f"Location: {loc}. Recent events: {events[:5]}. Active: {quests}"
).tolist()
hits = index.query(vector=query_embedding, top_k=5,
                   include_metadata=True, namespace=uuid)
rag_context = "\n---\n".join(h["metadata"]["text"] for h in hits)
# → injected into the LLM prompt as "PREVIOUS MEMORIES:"
```

### Cleanup

- On `game_over`: `index.delete(namespace=uuid)`
- On stale state (1h TTL expiry): same delete via the stale-cleanup sweep (C7) — a locally saved blob can still restore it on entry
- **Exit**: never deletes vectors automatically. Save → the client dumps the namespace via `index.range()` (vectors included, no re-embedding on restore). Don't save → optional `index.delete(namespace=uuid)`.
- **Autosave**: every 10 messages the drain fires and the client refreshes its saved blob (worst case on crash: 10 messages lost).
- **Entry / resume**: found + Redis state alive → continue live; found + expired → `POST /memory/restore` upserts the saved chunks back into the namespace; new scenario → fresh namespace.

Server contract + client ownership split: `REDIS_API.md` → "Scenario Lifecycle".

---

## Embedding model

| Setting | Value |
|---------|-------|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Dimension | 384 |
| Chunk size | 10k tokens (`len(text) // 4`), paragraph boundaries |
| Same model for write + query | **required** — mismatch silently degrades recall |

`pip install upstash-vector sentence-transformers`

---

## Costs (free tier)

| Component | Cost |
|-----------|------|
| Game Server (Railway) | Free credits |
| Upstash Redis (free tier) | $0 |
| Upstash Vector (free tier: 200M vectors×dims, 10k queries/day, 1GB) | $0 |
| sentence-transformers (local) | $0 |
| **Total** | **$0/month** |

Scale: ~200 chunks × 3KB per long session ≈ 600KB/session → 100+ sessions fit the free tier comfortably. Queries are the tighter limit: 10k/day ≈ 1 query per turn with 10k turns/day of headroom.
