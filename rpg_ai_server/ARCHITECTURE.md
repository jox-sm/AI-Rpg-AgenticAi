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

**Asynchronous D&D RPG AI Server** built with **LangGraph**, **LangChain**, and **Google Gemini SDK**. Processes game requests via Redis queue through a 7-node LangGraph pipeline (3 conditional service nodes, 2 main processing nodes, 1 reactive tool agent, 1 output node), pushing results to a second Redis DB.

**Key principles:** Strict separation of concerns | Multi-tenant async concurrency | Memory-aware throttling | API-agnostic model layer via OpenRouter.

---

## 2. System Architecture

### Data Flow
1. **Frontend** pushes `{uuid, prompt, data, images}` into **Redis DB 0**
2. **MultiTaskEngine** polls DB 0, spawns concurrent `asyncio` tasks
3. Each request runs the LangGraph pipeline: `Node5 (context) → Router → [Node1/2/3 if needed, loop] → Node4 (tools) → Node6 (story) → Node7 (output)`
4. Result pushed to **Redis DB 1**; frontend reads by UUID

---

## 3. Directory Structure & Separation of Concerns

```
rpg_ai_server/
├── main.py                         # Entry point, signal handlers
├── config/                         # Environment & configuration
│   ├── settings.py                 # Pydantic config from .env
│   └── models.py                   # Model factories
├── schemas/                        # Data contracts
│   ├── enums.py                    # 8 enums (Terrain, TimeOfDay, EntityType...)
│   ├── types.py                    # 14 Pydantic models
│   └── state.py                    # LangGraph GameState TypedDict
├── redis/                          # Persistence & queueing
│   ├── client.py                   # Base + InputRedisClient + OutputRedisClient
│   ├── input_queue.py              # Poll/pop from DB 0
│   └── output_cache.py             # Push + memory monitoring to DB 1
├── agents/                         # AI/LLM business logic
│   ├── node1_web_search.py         # Gemini web search
│   ├── node2_image_processor.py    # Image → 15×15 grid (Nemotron)
│   ├── node3_redescriptor.py       # Re-description (OWL-alpha)
│   ├── node4_tool_agent/           # 6 D&D tools + create_agent
│   ├── node5_context_injector.py   # Context summarization (Nemotron Super)
│   ├── node6_story_generator.py    # Story generation (Qwen Coder)
│   └── node7_output_pusher.py      # Result → Redis DB 1
├── engine/                         # Orchestration
│   ├── graph_builder.py            # StateGraph + router
│   ├── orchestrator.py             # GameOrchestrator
│   └── multi_tasker.py             # MultiTaskEngine, backpressure
├── utils/                          # Shared utilities
│   ├── logger.py                   # Structured logging
│   └── openrouter_client.py        # Direct HTTP client for OpenRouter
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

**Two databases:** DB 0 (Input) — request queue `uuid → {prompt, data, images, timestamp}`, TTL 1h; DB 1 (Output) — result cache `uuid → {game_data, story, context_summary, timestamp}`, TTL 1h.

**`redis/client.py`** — `RedisClient` wraps `redis.asyncio.Redis` with `set_json/get_json/memory_percent()`. Subclasses: `InputRedisClient` adds `pop_request()`, `OutputRedisClient` adds `push_result()`.

**`redis/input_queue.py`** — `InputQueue`: `next_request()` → pops first key from DB 0, returns `GameRequest` or `None`; `queue_size()`.

**`redis/output_cache.py`** — `OutputCache`: `store_result()` → pushes to DB 1; `memory_pressure_ok()` → checks maxmemory threshold; `count()`.

---

## 5. LangGraph Orchestrator

### Graph Structure (`engine/graph_builder.py`)
Pipeline: `START → Node5 → Router → (Node1|Node2|Node3 loop) → Node4 → Node6 → Node7 → END`

### Router Logic
Priority: `needs_search` → Node1, `needs_image_processing` → Node2, `needs_re_description` → Node3. After any conditional completes, `route_from_conditional()` re-checks flags — if any still `True`, loops to Router; else proceeds to Node4.

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
```

---

## 6. Node Deep Dive

### Node 1 — Gemini Web Search (Conditional)
`agents/node1_web_search.py` — **Model:** `gemini-2.0-flash` via `langchain-google-genai`. **Trigger:** real-world lore, rules, or current facts needed. Creates `ChatGoogleGenerativeAI`, binds `google_search` tool, invokes LangChain agent. Sets `state["search_results"]`, clears `needs_search`. Gemini chosen for native Google Search grounding with citations.

### Node 2 — Image Processor (Conditional)
`agents/node2_image_processor.py` — **Model:** `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` via OpenRouter direct HTTP. **Trigger:** images in request. Iterates images, prompts for **15×15 grid** (225 cells) with `response_format: json_object`. Each cell: `items[], ores[], entities[], terrain, prerequisites[], cell[x,y], description`. Validates into `GridCell` Pydantic models, sets `needs_image_processing = False`. 15×15 = ∼150ft × 150ft encounter area at 10ft/cell.

### Node 3 — Re-Description Engine (Conditional)
`agents/node3_redescriptor.py` — **Model:** `openrouter/owl-alpha` (1M context) via OpenRouter. **Trigger:** in-game time passage requiring environment updates. Receives grid + time change; model changes entities (nocturnal/undead at night), keeps items/ores static, updates descriptions. OWL-alpha's 1M context handles full 225-cell grid in one pass.

### Node 4 — Tool Agent (Reactive)
`agents/node4_tool_agent/` — **Model:** `qwen/qwen3-coder:free` via OpenRouter. LangChain `create_agent` with `MemorySaver`. **6 tools:**
- `dice_roller(dice, count, advantage, disadvantage, modifier, reason)` — d4–d100, advantage/disadvantage
- `damage_multiplier(base_damage, damage_type, monster_type, position, ...)` — elemental × positional multipliers
- `stats_multiplier_and_updater(stats, monster, exp, difficulty)` — built-in XP table, level-up logic
- `skill_updater_and_validator(skills, action, ...)` — cooldowns, sacrifice-to-evolve mechanic
- `inventory_checker_and_updater(inventory, action, ...)` — currency-aware (gold/silver/copper/platinum)
- `json_data_maker_and_tracker(action, ...)` — arbitrary structured data, relationship system (−100 to +100)

Agent loop: reduce cooldowns → process combat → check inventory → update relationships → return summary.

### Node 5 — Context Injector (Main)
`agents/node5_context_injector.py` — **Model:** `nvidia/nemotron-3-super-120b-a12b:free` via OpenRouter. First node. Collects all game state (prompt, input, grid, search, tools), compresses into `ContextSummary` JSON: `active_quests, current_location, party_members, recent_events, inventory_summary, key_items, time_of_day, weather, narrative_context`. 120B model excels at structured extraction.

### Node 6 — Story Generator (Main)
`agents/node6_story_generator.py` — **Model:** `qwen/qwen3-coder:free` via OpenRouter. After Node 4. Aggregates context + grid + tool results; generates narrative (2nd person POV, <500 words, D&D 5e flavor, temperature 0.7). Stores in `state["story_output"]`.

### Node 7 — Output Pusher
`agents/node7_output_pusher.py` — Final node. Builds `GameOutput` (uuid, game_data, story, context_summary, timestamp), calls `OutputCache.store_result()`, sets `state["processed"] = True`.

---

## 7. Model Configuration

| Node | Model | Provider | Via | Temp | Max Tokens |
|------|-------|----------|-----|------|------------|
| 1 | `gemini-2.0-flash` | Google | `langchain-google-genai` | 0.3 | Default |
| 2 | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | OpenRouter | Direct HTTP | 0.1 | 8,192 |
| 3 | `openrouter/owl-alpha` | OpenRouter | Direct HTTP | 0.2 | 65,536 |
| 4 | `qwen/qwen3-coder:free` | OpenRouter | `langchain-openai` | 0.3 | 8,192 |
| 5 | `nvidia/nemotron-3-super-120b-a12b:free` | OpenRouter | Direct HTTP | 0.1 | 2,048 |
| 6 | `qwen/qwen3-coder:free` | OpenRouter | Direct HTTP | 0.7 | 8,192 |

**Two API patterns:** Nodes 1 & 4 use LangChain wrappers (need agent/tool-calling loop). Nodes 2,3,5,6 use direct HTTP (simpler prompt→response, finer control over `response_format`).

---

## 8. Multi-Tasking Engine

`engine/multi_tasker.py` — `MultiTaskEngine` with `asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)` (default 100). Per-request: pop from Redis → acquire semaphore → `asyncio.create_task()`. Completion callbacks auto-clean active task set.

**Main loop:** `while running: check memory pressure (every 100 reqs) → pop request → acquire semaphore → create task → track → repeat`

**Memory backpressure:** Every 100 requests, checks Redis output DB memory %. If ≥90%: back off 3s, recheck, loop until <90%.

---

## 9. Throttling & Backpressure

| Layer | Mechanism | Scope | Trigger |
|-------|-----------|-------|---------|
| 1. Concurrency cap | `asyncio.Semaphore` | Per-request | Reaches `MAX_CONCURRENT_REQUESTS` (100) |
| 2. Memory monitoring | Redis `INFO memory` | Per-100-requests | Output DB > 90% |
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

**Prerequisites:** Python 3.10+, Redis, OpenRouter API key, Google Gemini API key.

```bash
cd rpg_ai_server
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # edit with your keys
```

**Required env vars:** `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`.

**Run:** `redis-server` then `python -m rpg_ai_server.main`.

**Test:** Push to DB 0 via `redis-cli -n 0 SET <uuid> '{...}' EX 3600`, read result from DB 1 via `redis-cli -n 1 GET <uuid>`.

---

## 12. Configuration Reference

```
Settings
├── redis: RedisConfig          host, port (6379), input_db (0), output_db (1), password?, ttl (3600)
├── models: ModelConfig         gemini_model, image_model, redescription_model,
│                               tool_agent_model, context_injector_model, story_model
└── app: AppConfig              max_concurrent (100), memory_threshold (90%), backoff (3s),
                                log_level (INFO), openrouter_api_key?, openrouter_base_url,
                                google_api_key?
```

---

## Appendix A: LangGraph Concepts Used

| Concept | Location | Purpose |
|---------|----------|---------|
| `StateGraph` | `graph_builder.py` | Graph construction |
| `TypedDict` state | `schemas/state.py` | Typed shared state |
| `Annotated[list, operator.add]` | `schemas/state.py` | Accumulating reducers |
| `add_node()` | `graph_builder.py` | Register 7 nodes + router |
| `add_edge()` | `graph_builder.py` | Fixed edges (START→N5, N4→N6→N7→END) |
| `add_conditional_edges()` | `graph_builder.py` | Router + loop-back |
| `create_agent` | Nodes 1 & 4 | Tool-calling agent loops |
| `MemorySaver` | Node 4 | Agent memory for tool loop |

## Appendix B: OpenRouter Direct Client

`utils/openrouter_client.py` — wraps `httpx.AsyncClient`: `chat_completion()` with optional `response_format`, `extract_json()` convenience, auto-injected headers, 120s timeout for OWL-alpha. Used by Nodes 2,3,5,6.

## Appendix C: Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Two Redis databases | Different access patterns (FIFO pop vs keyed read) and lifecycles |
| Conditional flags in state | Clean router decisions without hardcoded flow |
| Separate tool agent | Complex game mechanics warrant dedicated agent with 6 tools |
| Context as first node | Prevents token overflow for downstream nodes |
| Direct HTTP for most nodes | Faster and more controllable than LangChain wrappers |
| `asyncio.Semaphore` | Simpler than thread pool; all operations are async |
| Memory check every 100 requests | Balances overhead with responsiveness |
