# D&D RPG AI Server — Architecture Document

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Directory Structure & Separation of Concerns](#3-directory-structure--separation-of-concerns)
4. [Redis Layer](#4-redis-layer)
5. [LangGraph Orchestrator](#5-langgraph-orchestrator)
6. [Node Deep Dive](#6-node-deep-dive)
7. [Model Configuration](#7-model-configuration)
8. [Multi-Tasking Engine](#8-multi-tasking-engine)
9. [Throttling & Backpressure](#9-throttling--backpressure)
10. [Edge Cases & Defensive Design](#10-edge-cases--defensive-design)
11. [Setup & Running](#11-setup--running)
12. [Configuration Reference](#12-configuration-reference)

---

## 1. Project Overview

**Asynchronous D&D RPG AI Server** built with **LangGraph** and **LangChain**, **OpenRouter-only** for all LLM calls (no Gemini SDK, no Google key). Processes game requests via a single Upstash Redis (prefix-separated queue/state/output) through a v2 LangGraph graph: entry classifier → re-entrant ReAct router over 3 conditional service nodes → parallel pure mechanics fan-out → context refresh → summarizer → story → pusher.

**Key principles:** Strict separation of concerns | Multi-tenant async concurrency | Memory-aware throttling | API-agnostic model layer via OpenRouter.

---

## 2. System Architecture

### Data Flow
1. **Frontend** pushes `{uuid, prompt, data, images}` into Upstash Redis under the **`input:`** prefix
2. **MultiTaskEngine** polls `input:`, spawns concurrent `asyncio` tasks (semaphore cap 16)
3. Each request runs the v2 graph: `classifier → react_router ⇄ {search | image | redescribe} (≤3 passes) → mechanics (6 parallel pure sub-nodes) → context_refresh → summarizer → story → pusher`
4. Result pushed under the **`output:`** prefix (long-lived game state under **`games:`**); frontend reads by UUID

---

## 3. Directory Structure & Separation of Concerns

```
rpg_ai_server/
├── main.py                         # Entry point, signal handlers
├── config/                         # Environment & configuration
│   └── settings.py                 # Env-driven config (redis/models/search/app)
├── schemas/                        # Data contracts
│   ├── enums.py                    # 8 enums (Terrain, TimeOfDay, EntityType...)
│   ├── types.py                    # 14 Pydantic models
│   └── state.py                    # LangGraph GameState TypedDict
├── redis/                          # Persistence & queueing (single Upstash, prefixes)
│   ├── client.py                   # Base RedisClient (upstash_redis AsyncRedis REST) + Input/Output/Games clients (prefixes input:/output:/games:)
│   ├── queue.py                    # QueueManager (retries/delayed/dead) + InputQueue adapter
│   ├── game_state.py               # Per-game state, locks, story-buffer drain (threshold 25)
│   ├── vector_memory.py            # Upstash Vector game memory (drain target)
│   └── output_cache.py             # Push + memory monitoring to output: prefix
├── agents/                         # AI/LLM business logic (one node per file, no compat shims)
│   ├── classifier.py               # Entry intent classifier (deterministic fast-path + LLM via chat_json)
│   ├── node0_worldgen.py           # Deterministic living world (movement/expansion/day clock, no LLM)
│   ├── node1_web_search.py         # Scrapy lore scrape (httpx + scrapy.Selector, no key)
│   ├── node2_image_processor.py    # Image → 15×15 grid (Nemotron Nano)
│   ├── node3_redescriptor.py       # Re-description (gemma-4-26b)
│   ├── node4_parallel.py           # 6 pure mechanics sub-nodes (parallel fan-out, ordered merge)
│   ├── flee.py                     # Pack engagement + flee resolution + jev trick adjudication
│   ├── node5_context_injector.py   # Context summarization (gemma-4-31b)
│   ├── node6_story_generator.py    # Story generation (qwen3.8-27b)
│   └── node7_output_pusher.py      # Result → output: prefix
├── engine/                         # Orchestration (single graph, no v1/v2 duality)
│   ├── graph_v2.py                 # StateGraph (classifier → worldgen → react router → mechanics → story → pusher)
│   ├── orchestrator.py             # GameOrchestrator (rolling context/chat_log, allowlist merge)
│   └── multi_tasker.py             # MultiTaskEngine, backpressure
├── scripts/                        # Pure game systems (no LLM, no Redis)
│   ├── world_generator.py          # Seeded infinite world (deterministic cells, border expansion)
│   ├── combat_system.py            # resolve_attack / dodge / block / armor / statuses
│   ├── dice_engine.py              # d4–d100, advantage, skill checks
│   └── xp_loot.py                  # Rarity XP formula, DB loot rolls, adaptive-difficulty scalar
├── tests/                          # Hard-test files (graph_v2, orchestrator, atomic redis/engine, loops, queue, locks)
│   ├── test_graph_v2.py / test_orchestrator_hard.py / test_engine_atomic.py / ...
├── utils/                          # Shared utilities
│   ├── logger.py                   # Structured logging
│   ├── openrouter_client.py        # Direct HTTP client for OpenRouter (+ chat_json helper)
│   ├── coerce.py                   # as_dict/stat_of/to_int — dict-or-model state coercions
│   └── items_db.py                 # In-memory items database
├── requirements.txt
└── .env.example
```

| Concern | Module | Rationale |
|---------|--------|-----------|
| Data contracts | `schemas/` | Single source of truth for all types |
| Configuration | `config/` | Zero hardcoded values, all env-driven |
| LLM calls | `agents/` | Isolated business logic, independently testable |
| Orchestration | `engine/` | Pure routing, no business logic |
| Persistence | `redis/` | Swappable (Redis ↔ PostgreSQL) |
| Utilities | `utils/` | Shared HTTP, logging — zero business logic |

---

## 4. Redis Layer

**Single Upstash Redis, three prefixes:** `input:` (request queue `uuid → {prompt, data, images, timestamp}`, TTL 1h); `output:` (result cache `uuid → {game_data, story, context_summary, timestamp}`, TTL 1h); `games:` (long-lived per-game state hash + lock + story buffer/counter for vector-memory drain). `REDIS_HOST`/`PORT`/`DBs` remain only as an unused local fallback; production uses `UPSTASH_REDIS_REST_URL`/`TOKEN`.

**`redis/client.py`** — `RedisClient` wraps `upstash_redis.AsyncRedis` (REST) with `set_json/get_json/memory_percent()` and prefix namespacing. Subclasses: `InputRedisClient` (`prefix="input:"`) adds `pop_request()`, `OutputRedisClient` (`prefix="output:"`) adds `push_result()`, `GamesRedisClient` (`prefix="games:"`) adds hash/lock/counter ops.

**`redis/queue.py`** — queue helpers shared by the poll loop.

**`redis/queue.py`** — `QueueManager` (retries/delayed/dead + single-mover guard) plus the thin `InputQueue` pop/enqueue adapter.

**`redis/game_state.py`** — `GameStateManager`: per-game lock, allowlist state load/save, story-buffer append + `try_drain()` → exports overflow to vector memory every 25 turns (`DRAIN_THRESHOLD`).

**`redis/vector_memory.py`** — `GameMemory`: Upstash Vector namespaced per game (`{sid}:` id prefix); drain target for the story buffer.

**`redis/output_cache.py`** — `OutputCache`: `store_result()` → pushes under `output:`; `memory_pressure_ok()` → checks maxmemory threshold; `count()`.

---

## 5. LangGraph Orchestrator

### Graph Structure (`engine/graph_v2.py`)
Topology: `START → classifier → worldgen → react_router ⇄ {search | image | redescribe} (≤3 passes) → mechanics → context_refresh → summarizer → story → pusher → END`.

### Router Logic (ReAct)
Entry `classifier_node` writes a `DecisionReport` (intent, monster_move, buffs/debuffs, `needs_search/image/redescribe`) and mirrors legacy `needs_*` flags. `react_router` picks `next_node` among `search | image |redescribe | mechanics | story` (priority search → image → redescribe, re-entrant so image+search both happen across passes). Budget-first terminators force to `story`: passes ≥ `ROUTER_MAX_PASSES` (3), LLM calls ≥ `MAX_LLM_CALLS_PER_TURN` (12), or elapsed ≥ `REQUEST_TIMEOUT_SECONDS` (60s). Tool nodes loop back to the router while flags remain, else fall through to `mechanics`.

### context_refresh
Runs after mechanics: appends the last tool summary to the rolling `context` string (capped at `CONTEXT_MAX_CHARS`, 8000), no LLM. Full `summarizer` (Node 5) still runs after it so story sees fresh results.

### State Schema (`schemas/state.py`)
```python
class GameState(TypedDict):
    uuid: str; prompt: str; input_data: Dict; game_data: Dict
    images: Dict[str, ImageData]; grid_data: Dict[str, List[GridCell]]
    re_description_data: Optional[ReDescriptionData]
    context_summary: Optional[ContextSummary]
    character_stats: Optional[CharacterStats]
    skills: Annotated[List[Skill], operator.add]
    inventory: Annotated[List[InventoryItem], operator.add]
    relationships: Annotated[List[Relationship], operator.add]
    story_output: str; decision: Optional[NodeDecision]
    needs_search: bool; needs_image_processing: bool; needs_re_description: bool
    processed: bool; error: Optional[str]; search_results: str
    tool_results: Annotated[List[str], operator.add]
    game_output: Optional[Dict]; __next__: str
    # v2 additions
    context: str; chat_log: List[ChatMessage]  # rolling memory (8000 chars / 40 turns)
    decision_report: Optional[DecisionReport]; budget: Optional[BudgetUsage]
    next_node: str; router_trace: List[Dict[str, Any]]; force_exit_reason: Optional[str]
    conditional_passes: int; remaining_steps: int; turn_id: str
```

---

## 6. Node Deep Dive

### Classifier — Intent Classifier (Entry)
`agents/classifier.py` — **Model:** `liquid/lfm-2.5-2.6b:free` via OpenRouter direct HTTP. **Two stages:** deterministic fast-path first (images attached → image flag; time-change keywords → redescribe flag; lore keywords → search flag — no LLM cost), then LLM JSON classification (intent, target, monster_move, buffs/debuffs, needs_* flags, confidence; confidence < 0.6 routes straight to mechanics). Writes `decision_report` + mirrors legacy `needs_*` flags for the router.

### Node 1 — Scrapy Lore Search (Conditional)
`agents/node1_web_search.py` — **No model, no Google key.** `scrapy_lore_search` tool fetches SRD-legal D&D sources via `httpx` and parses readable text with `scrapy.Selector` (script/style/nav stripped, 1500-char cap). **Trigger:** lore/rules outside state. Sets `state["search_results"]`, clears `needs_search`. (Legacy `google_web_search` alias kept so old imports don't break.) Scraper tuned via `SCRAPER_USER_AGENT` / `SCRAPER_TIMEOUT_SECONDS` (15s) / `SCRAPER_CACHE_TTL_SECONDS` (86400).

### Node 2 — Image Processor (Conditional)
`agents/node2_image_processor.py` — **Model:** `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` via OpenRouter direct HTTP. **Trigger:** images in request. Iterates images, prompts for **15×15 grid** (225 cells) with `response_format: json_object`. Each cell: `items[], ores[], entities[], terrain, prerequisites[], cell[x,y], description`. Validates into `GridCell` Pydantic models, sets `needs_image_processing = False`. 15×15 = ∼150ft × 150ft encounter area at 10ft/cell.

### Node 3 — Re-Description Engine (Conditional)
`agents/node3_redescriptor.py` — **Model:** `google/gemma-4-26b-a4b-it:free` via OpenRouter. **Trigger:** in-game time passage requiring environment updates. Receives grid + time change; model changes entities (nocturnal/undead at night), keeps items/ores static, updates descriptions.

### Node 4 — Parallel Mechanics (Fan-out)
`agents/node4_parallel.py` — **No LLM (pure code).** Each of 6 sub-nodes (dice, damage, stats, skill, inventory, json) gets a deep-copied immutable snapshot of state, runs concurrently via `asyncio.gather`, and merges deterministically in order (dice→damage→stats→skill→inventory→json). No Redis writes here (merge + pusher own persistence); idempotent via `turn_id`. **6 tools (semantics unchanged):**
- `dice_roller(dice, count, advantage, disadvantage, modifier, reason)` — d4–d100, advantage/disadvantage
- `damage_multiplier(base_damage, damage_type, monster_type, position, ...)` — elemental × positional multipliers
- `stats_multiplier_and_updater(stats, monster, exp, difficulty)` — built-in XP table, level-up logic
- `skill_updater_and_validator(skills, action, ...)` — cooldowns, sacrifice-to-evolve mechanic
- `inventory_checker_and_updater(inventory, action, ...)` — currency-aware (gold/silver/copper/platinum)
- `json_data_maker_and_tracker(action, ...)` — arbitrary structured data, relationship system (−100 to +100)

Agent loop: reduce cooldowns → process combat → check inventory → update relationships → return summary.

### Node 5 — Context Injector / Summarizer (Main)
`agents/node5_context_injector.py` — **Model:** `google/gemma-4-31b-it:free` via OpenRouter. Runs after `context_refresh`. Collects all game state (prompt, input, grid, search, tools), compresses into `ContextSummary` JSON: `active_quests, current_location, party_members, recent_events, inventory_summary, key_items, time_of_day, weather, narrative_context`.

### Node 6 — Story Generator (Main)
`agents/node6_story_generator.py` — **Model:** `qwen/qwen3.8-27b:free` via OpenRouter. After the summarizer. Aggregates context + grid + tool results; generates narrative (2nd person POV, <500 words, D&D 5e flavor, temperature 0.7). Stores in `state["story_output"]`.

### Node 7 — Output Pusher
`agents/node7_output_pusher.py` — Final node. Builds `GameOutput` (uuid, game_data, story, context_summary, timestamp), calls `OutputCache.store_result()` (Upstash `output:` prefix), sets `state["processed"] = True`.

---

## 7. Model Configuration

| Stage | Model | Provider | Via | Temp | Max Tokens |
|------|-------|----------|-----|------|------------|
| classifier | `liquid/lfm-2.5-2.6b:free` | OpenRouter | Direct HTTP | 0.0 | 512 |
| search (Node 1) | — (Scrapy: httpx + scrapy.Selector) | — | — | — | — |
| 2 (image) | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | OpenRouter | Direct HTTP | 0.1 | 8,192 |
| 3 (redescribe) | `google/gemma-4-26b-a4b-it:free` | OpenRouter | Direct HTTP | 0.2 | 32,768 |
| 4 (mechanics) | — (6 pure sub-nodes, no LLM) | — | — | — | — |
| 5 (context) | `google/gemma-4-31b-it:free` | OpenRouter | Direct HTTP | 0.1 | 4,096 |
| 6 (story) | `qwen/qwen3.8-27b:free` | OpenRouter | Direct HTTP | 0.7 | 16,384 |

**Single API pattern:** all LLM calls go via the shared `chat_json` helper on the direct-HTTP OpenRouter client (`response_format` control, per-call timeouts). No LangChain wrappers, no Gemini SDK, no Google key.

---

## 8. Multi-Tasking Engine

`engine/multi_tasker.py` — `MultiTaskEngine` with `asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)` (default 16). Per-request: pop from Redis → acquire semaphore → `asyncio.create_task()`. Completion callbacks auto-clean active task set.

**Main loop:** `while running: check memory pressure (every 100 reqs) → pop request → acquire semaphore → create task → track → repeat`

**Memory backpressure:** Every 100 requests, checks Upstash output memory %. If ≥90%: back off 3s, recheck, loop until <90%.

---

## 9. Throttling & Backpressure

| Layer | Mechanism | Scope | Trigger |
|-------|-----------|-------|---------|
| 1. Concurrency cap | `asyncio.Semaphore` | Per-request | Reaches `MAX_CONCURRENT_REQUESTS` (16) |
| 2. Memory monitoring | Upstash `INFO memory` | Per-100-requests | Output data > 90% |
| 3. Empty queue backoff | `await asyncio.sleep(0.1)` | Per-iteration | No requests in queue |

---

## 10. Edge Cases & Defensive Design

| # | Edge Case | Handling |
|---|-----------|----------|
| 1 | Empty input queue | 100ms sleep, retry |
| 2 | Redis connection failure | Idempotent `connect()`, methods return `None`/`False` |
| 3 | Model API timeout | `try/except` per node, error in state, pipeline continues |
| 4 | Memory pressure spike | Back off 3s, recheck, loop |
| 5 | No images | Immediate return if `state["images"]` empty |
| 6 | No re-description data | Immediate return if missing |
| 7 | Orphaned requests | Redis TTL auto-expires (1h default) |
| 8 | Concurrent storm (100+) | Semaphore queues excess tasks |
| 9 | State explosion | Context summarization caps at 500 chars |
| 10 | Grid parsing failure | Per-image try/catch, continues with remaining |
| 11 | Tool agent infinite loop | LangChain recursion limit + bounded execution |
| 12 | Windows compatibility | Falls back to no-signal mode |
| 13 | Invalid dice type | Returns error JSON |
| 14 | Inventory overflow | Unbounded (no hard D&D cap); summarizer handles counts |
| 15 | Duplicate UUID | Last-write-wins; first write's TTL cleans up |

---

## 11. Setup & Running

**Prerequisites:** Python 3.10+, Upstash Redis (REST URL + token), OpenRouter API key. No Google/Gemini key needed (Node 1 uses Scrapy).

```bash
cd rpg_ai_server
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # edit with your keys (placeholders only — never commit secrets)
```

**Required env vars:** `OPENROUTER_API_KEY`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`.

**Run:** `python -m rpg_ai_server.main`.

**Test:** Push to the `input:` prefix, read result from the `output:` prefix by UUID (see `tests/test_queue.py`, `tests/test_redis_api.py`).

---

## 12. Configuration Reference

```
Settings
├── redis: RedisConfig          upstash_rest_url/token (single Upstash, prefixes input:/output:/games:),
│                               host/port/input_db/output_db/password?/ttl (3600) as unused local fallback
├── models: ModelConfig         classifier_model (lfm-2.5), image_model (nemotron-nano),
│                               redescription_model (gemma-4-26b), story_model (qwen3.8-27b),
│                               context_injector_model (gemma-4-31b), jev_model (qwen3.8-27b, trick adjudication),
│                               scraper_user_agent/timeout/cache_ttl
├── search: SearchConfig        upstash_search_url/token?, index_name, top_k, reranking, weights/chunking
└── app: AppConfig              max_concurrent (16), memory_threshold (90%), backoff (3s),
                                log_level (INFO), openrouter_api_key?, openrouter_base_url,
                                loop_recursion_limit (60), router_max_passes (3), max_tool_calls (15),
                                request_timeout (60s), locks (ttl 30s / refresh 10s),
                                max_llm_calls_per_turn (12), max_tokens_per_turn (24000),
                                context_max_chars (8000), chat_log_max_turns (40), drain_threshold (25)
```

---

## Appendix A: LangGraph Concepts Used

| Concept | Location | Purpose |
|---------|----------|---------|
| `StateGraph` | `graph_v2.py` | Graph construction |
| `TypedDict` state | `schemas/state.py` | Typed shared state |
| `Annotated[list, operator.add]` | `schemas/state.py` | Accumulating reducers |
| `add_node()` | `graph_v2.py` | Register classifier + router + 3 conditionals + mechanics + refresh + summarizer + story + pusher |
| `add_edge()` | `graph_v2.py` | Fixed edges (START→classifier→router, mechanics→refresh→summarizer→story→pusher→END) |
| `add_conditional_edges()` | `graph_v2.py` | ReAct router + re-entrant tool loop-back |
| `asyncio.gather` fan-out | `node4_parallel.py` | 6 pure mechanics sub-nodes on immutable snapshots |

## Appendix B: OpenRouter Direct Client

`utils/openrouter_client.py` — wraps `httpx.AsyncClient`: `chat_completion()` with optional `response_format`, `extract_json()` convenience, auto-injected headers, 120s default timeout. Used by the classifier and Nodes 2,3,5,6. (Node 1 needs no LLM — Scrapy; Node 4 is pure code.)

## Appendix C: Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single Upstash Redis with prefixes | One managed instance; `input:`/`output:`/`games:` separate queue, results, and long-lived state without multi-DB ops |
| Entry classifier + ReAct router | Cheap deterministic fast-path first; LLM only when ambiguous; re-entrant passes handle multi-need turns |
| Budget terminators (passes/calls/deadline) | Force-to-story guarantees bounded latency and cost per turn |
| Parallel pure mechanics (Node 4) | Snapshot fan-out + ordered merge: no shared mutable state, no races, deterministic |
| Rolling `context` string + `chat_log` caps | 8000-char context + 40-turn log keep prompts bounded; vector drain every 25 turns preserves history |
| Context refresh after mechanics | Story/summarizer see fresh tool results (was stale context-first) |
| Direct HTTP for all LLM calls | Faster and more controllable than LangChain wrappers; single client, uniform `response_format` |
| `asyncio.Semaphore` (16) | Simpler than thread pool; all operations are async; 16 bounds Upstash + LLM concurrency |
| Memory check every 100 requests | Balances overhead with responsiveness |
