# D&D RPG AI Server — Architecture Document

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Directory Structure & Separation of Concerns](#3-directory-structure--separation-of-concerns)
4. [Redis Layer](#4-redis-layer)
5. [LangGraph Orchestrator](#5-langgraph-orchestrator)
6. [Node Deep Dive](#6-node-deep-dive)
   - [Node 1 — Gemini Web Search (Conditional)](#node-1--gemini-web-search-conditional)
   - [Node 2 — Image Processor (Conditional)](#node-2--image-processor-conditional)
   - [Node 3 — Re-Description Engine (Conditional)](#node-3--re-description-engine-conditional)
   - [Node 4 — Tool Agent (Reactive)](#node-4--tool-agent-reactive)
   - [Node 5 — Context Injector (Main)](#node-5--context-injector-main)
   - [Node 6 — Story Generator (Main)](#node-6--story-generator-main)
   - [Node 7 — Output Pusher](#node-7--output-pusher)
7. [Model Configuration](#7-model-configuration)
8. [Multi-Tasking Engine](#8-multi-tasking-engine)
9. [Throttling & Backpressure](#9-throttling--backpressure)
10. [Edge Cases & Defensive Design](#10-edge-cases--defensive-design)
11. [Setup & Running](#11-setup--running)
12. [Configuration Reference](#12-configuration-reference)

---

## 1. Project Overview

This is an **asynchronous D&D RPG AI Server** built using **LangGraph**, **LangChain**, and the **Google Gemini SDK**. It processes game requests via a Redis queue, runs them through a 7-node LangGraph pipeline (with 3 conditional service nodes, 2 main processing nodes, 1 reactive tool agent, and 1 output node), and pushes results back to a second Redis database.

**Key design principles:**
- Strict **Separation of Concerns** — each concern (schemas, Redis, config, agents, orchestration) lives in its own directory
- **Multi-tenant by design** — the system processes many requests concurrently using `asyncio`
- **Memory-aware throttling** — monitors Redis output memory and backpressures when needed
- **API-agnostic model layer** — uses OpenRouter's unified API to swap models without code changes

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         External World                               │
│  ┌──────────┐    ┌──────────────┐    ┌──────────┐                   │
│  │ Frontend  │───▶│  Redis DB 0  │───▶│  Server  │                   │
│  │  (Game)   │    │  (Input)     │    │  (Main)  │                   │
│  └──────────┘    │  uuid:json   │    └──────────┘                   │
│                  └──────────────┘                                   │
│                         │                                            │
│                         ▼                                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    RPG AI Server                               │   │
│  │                                                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │              Multi-Task Engine (asyncio)                  │  │   │
│  │  │  ┌────────────────────────────────────────────────────┐   │  │   │
│  │  │  │           GameOrchestrator (per-request)           │   │  │   │
│  │  │  │  ┌──────────────────────────────────────────────┐  │   │  │   │
│  │  │  │  │         LangGraph Pipeline                    │  │   │  │   │
│  │  │  │  │                                                │  │   │  │   │
│  │  │  │  │  START → Node5 → Router ──→ Node1 (cond) ──→ │  │   │  │   │
│  │  │  │  │                    │                           │  │   │  │   │
│  │  │  │  │                    ├──→ Node2 (cond) ────→    │  │   │  │   │
│  │  │  │  │                    │                           │  │   │  │   │
│  │  │  │  │                    └──→ Node3 (cond) ────→    │  │   │  │   │
│  │  │  │  │                                                │  │   │  │   │
│  │  │  │  │                    ┌─→ Node4 (tool agent) ──→ │  │   │  │   │
│  │  │  │  │                    │                           │  │   │  │   │
│  │  │  │  │  ←────── Loop ─────┘                           │  │   │  │   │
│  │  │  │  │                                                │  │   │  │   │
│  │  │  │  │  Node4 → Node6 → Node7 → END                  │  │   │  │   │
│  │  │  │  └──────────────────────────────────────────────┘  │   │  │   │
│  │  │  └────────────────────────────────────────────────────┘   │  │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │                                                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                         │                                            │
│                         ▼                                            │
│                  ┌──────────────┐                                   │
│                  │  Redis DB 1   │                                   │
│                  │  (Output)     │                                   │
│                  │  uuid:json   │                                   │
│                  └──────────────┘                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow (A-to-Z)

1. **Frontend/backend** pushes a request as `{uuid, prompt, data, images}` into **Redis DB 0**
2. **MultiTaskEngine** polls Redis DB 0, pops requests, and spawns concurrent `asyncio` tasks
3. Each request runs through the **LangGraph pipeline**:
   - **Node 5** injects summarized context
   - **Router** checks if any conditional services are needed (search, image processing, re-description)
   - If conditionals are needed → Node 1/2/3 → loop back to Router
   - When no conditionals remain → **Node 4** (tool agent processes game mechanics)
   - **Node 6** generates story narrative
   - **Node 7** pushes `{uuid, gameData}` into **Redis DB 1**
4. **Frontend/backend** reads the result from Redis DB 1 by UUID

---

## 3. Directory Structure & Separation of Concerns

```
rpg_ai_server/
├── __init__.py                     # Package marker
├── main.py                         # Entry point — signal handlers, loop
│
├── config/                         # CONCERN: Environment & configuration
│   ├── __init__.py
│   ├── settings.py                 # Pydantic/dataclass config from .env
│   └── models.py                   # Model factories (Gemini, OpenRouter)
│
├── schemas/                        # CONCERN: Data definitions & contracts
│   ├── __init__.py
│   ├── enums.py                    # 8 enums: Terrain, TimeOfDay, EntityType, etc.
│   ├── types.py                    # 14 Pydantic models: GridCell, ImageData, GameRequest, etc.
│   └── state.py                    # LangGraph GameState TypedDict
│
├── redis/                          # CONCERN: Data persistence & queueing
│   ├── __init__.py
│   ├── client.py                   # Base Redis client + InputRedisClient + OutputRedisClient
│   ├── input_queue.py              # InputQueue — poll/pop from DB 0
│   └── output_cache.py             # OutputCache — push + memory monitoring to DB 1
│
├── agents/                         # CONCERN: AI/LLM business logic
│   ├── __init__.py
│   ├── node1_web_search.py         # Gemini SDK web search
│   ├── node2_image_processor.py    # Image → 15x15 grid (Nemotron via OpenRouter)
│   ├── node3_redescriptor.py       # Re-description (OWL-alpha via OpenRouter)
│   ├── node4_tool_agent/           # CONCERN: Game mechanics
│   │   ├── __init__.py
│   │   ├── tools.py                # 6 D&D tools (dice, damage, stats, skills, inventory, JSON tracker)
│   │   └── agent.py                # create_agent wrapping all 6 tools
│   ├── node5_context_injector.py   # Context summarization (Nemotron Super)
│   ├── node6_story_generator.py    # Story generation (Qwen Coder)
│   └── node7_output_pusher.py      # Result → Redis DB 1
│
├── engine/                         # CONCERN: Orchestration & workflow
│   ├── __init__.py
│   ├── graph_builder.py            # StateGraph construction + router logic
│   ├── orchestrator.py             # GameOrchestrator — builds initial state, invokes graph
│   └── multi_tasker.py             # MultiTaskEngine — async concurrency, backpressure
│
├── utils/                          # CONCERN: Cross-cutting utilities
│   ├── __init__.py
│   ├── logger.py                   # Structured logging
│   └── openrouter_client.py        # Direct HTTP client for OpenRouter API
│
├── requirements.txt                # Python dependencies
└── .env.example                    # Environment variable template
```

### Why this separation?

| Concern | Module | Why separated |
|---------|--------|--------------|
| **Data contracts** | `schemas/` | Every agent imports its types; changing a field updates everywhere consistently |
| **Configuration** | `config/` | No hardcoded values anywhere; all env-driven |
| **LLM calls** | `agents/` | Business logic isolated from orchestration; agents can be tested independently |
| **Orchestration** | `engine/` | Graph wiring is pure routing; no business logic leaks in |
| **Persistence** | `redis/` | Swappable — swap Redis for PostgreSQL by changing only this folder |
| **Utilities** | `utils/` | Shared HTTP clients, logging — zero business logic |

---

## 4. Redis Layer

### Two Redis Databases

| Database | Purpose | Key Format | TTL | Accessed By |
|----------|---------|------------|-----|-------------|
| **DB 0** (Input) | Request queue from frontend | `uuid → {prompt, data, images, timestamp}` | 1 hour | InputQueue |
| **DB 1** (Output) | Result cache for frontend | `uuid → {game_data, story, context_summary, timestamp}` | 1 hour | OutputCache |

### Key Files

**`redis/client.py`** — `RedisClient` base class wraps `redis.asyncio.Redis`:
- `set_json(key, value, ttl)` — serializes dict to JSON, stores with TTL
- `get_json(key)` — retrieves and deserializes
- `memory_percent()` — checks Redis `INFO memory` to compute used/max ratio
- `InputRedisClient` subclass adds `pop_request()` (get + delete atomically) and `get_all_keys()`
- `OutputRedisClient` subclass adds `push_result(uuid, data)`

**`redis/input_queue.py`** — `InputQueue` wraps InputRedisClient:
- `next_request()` → pops the first key from DB 0, returns `GameRequest` or `None`
- `queue_size()` → reports backlog depth

**`redis/output_cache.py`** — `OutputCache` wraps OutputRedisClient:
- `store_result(output)` → pushes `GameOutput` to DB 1
- `memory_pressure_ok()` → returns `False` if Redis maxmemory usage exceeds threshold
- `count()` → reports how many results are cached

---

## 5. LangGraph Orchestrator

### Graph Structure (`engine/graph_builder.py`)

```
                    ┌──────────────────────────────────────────────────┐
                    │                  START                            │
                    └────────────────────┬─────────────────────────────┘
                                         │
                                         ▼
                    ┌──────────────────────────────────────────────────┐
                    │          Node 5: Context Injector                 │
                    │  (Nemotron Super — summarizes state into JSON)    │
                    └────────────────────┬─────────────────────────────┘
                                         │
                                         ▼
                    ┌──────────────────────────────────────────────────┐
                    │                Router Node                        │
                    │  Checks needs_search, needs_image_processing,    │
                    │  needs_re_description flags                      │
                    └────┬──────────────┬──────────────┬───────────────┘
                         │              │              │
              ┌──────────┘    ┌─────────┘    ┌────────┘
              ▼                ▼              ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │  Node 1:     │ │  Node 2:     │ │  Node 3:     │
     │ Web Search   │ │ Image Proc   │ │ Re-Describe  │
     │ (Gemini)     │ │ (Nemotron)   │ │ (OWL-alpha)  │
     └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
            │                │                │
            └───────┬────────┘───────┬────────┘
                    ▼                ▼
         ┌──────────────────┐  ┌──────────────────┐
         │   needs more?    │  │     Done? Go     │
         │  Loop to Router  │  │   to Node 4      │
         └──────────────────┘  └────────┬─────────┘
                                        │
                                        ▼
                    ┌──────────────────────────────────────────────────┐
                    │     Node 4: Tool Agent (Reactive Loop)           │
                    │  ├─ dice_roller                                  │
                    │  ├─ damage_multiplier                            │
                    │  ├─ stats_multiplier_and_updater                 │
                    │  ├─ skill_updater_and_validator                  │
                    │  ├─ inventory_checker_and_updater                │
                    │  └─ json_data_maker_and_tracker                  │
                    └────────────────────┬─────────────────────────────┘
                                         │
                                         ▼
                    ┌──────────────────────────────────────────────────┐
                    │          Node 6: Story Generator                  │
                    │  (Qwen Coder — weaves mechanics into narrative)   │
                    └────────────────────┬─────────────────────────────┘
                                         │
                                         ▼
                    ┌──────────────────────────────────────────────────┐
                    │          Node 7: Output Pusher                    │
                    │  Serializes state → GameOutput → Redis DB 1      │
                    └────────────────────┬─────────────────────────────┘
                                         │
                                         ▼
                    ┌──────────────────────────────────────────────────┐
                    │                    END                             │
                    └──────────────────────────────────────────────────┘
```

### Router Logic

The Router node (`engine/graph_builder.py:make_router_node`) checks state flags in priority order:

1. If `state["needs_search"] = True` → route to **Node 1**
2. If `state["needs_image_processing"] = True` → route to **Node 2**
3. If `state["needs_re_description"] = True` → route to **Node 3**
4. Otherwise → route to **Node 4** (main pipeline continues)

After any conditional node completes, `route_from_conditional()` re-checks the flags:
- If any flag is still `True` → loop back to **Router**
- If all flags are `False` → proceed to **Node 4**

This allows the pipeline to invocate multiple conditionals in sequence before hitting the main tool agent.

### State Schema (`schemas/state.py`)

The LangGraph `GameState` is a `TypedDict` with reducers for accumulating fields:

```python
class GameState(TypedDict):
    uuid: str                                   # Unique game session ID
    prompt: str                                 # Original user prompt
    input_data: Dict                            # Raw input payload
    game_data: Dict                             # Accumulated game state
    images: Dict[str, ImageData]                # Image UUID → ImageData
    grid_data: Dict[str, List[GridCell]]        # Image UUID → 15x15 grid
    re_description_data: Optional[ReDescriptionData]
    context_summary: Optional[ContextSummary]
    character_stats: Optional[CharacterStats]
    skills: Annotated[List[Skill], operator.add]        # Accumulating list
    inventory: Annotated[List[InventoryItem], operator.add]
    relationships: Annotated[List[Relationship], operator.add]
    story_output: str                           # Final narrative
    decision: Optional[NodeDecision]
    needs_search: bool                          # Conditional flags
    needs_image_processing: bool
    needs_re_description: bool
    processed: bool
    error: Optional[str]
    search_results: str
    tool_results: Annotated[List[str], operator.add]
    game_output: Optional[Dict]
    __next__: str                               # Router destination
```

---

## 6. Node Deep Dive

### Node 1 — Gemini Web Search (Conditional)

**File:** `agents/node1_web_search.py`
**Model:** `gemini-2.0-flash` (Google Gemini via `langchain-google-genai`)
**Trigger:** When the game needs real-world lore, rules lookup, or current facts

**How it works:**
1. Creates a `ChatGoogleGenerativeAI` instance with the Gemini model
2. Binds the `google_search` tool to enable Google Search grounding
3. Creates a LangChain `create_agent` with one tool: `google_web_search(query)`
4. Invokes the agent with the game prompt + UUID context
5. Returns the search results in `state["search_results"]`
6. Sets `state["needs_search"] = False`

**Why Gemini specifically:**
Gemini has native Google Search grounding built into the API. When you bind the `google_search` tool, the model retrieves real-time web results with citations. This is more reliable than Tavily or other web search APIs for RPG lore queries.

---

### Node 2 — Image Processor (Conditional)

**File:** `agents/node2_image_processor.py`
**Model:** `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` via OpenRouter
**Trigger:** When the game request contains images that need environmental analysis

**How it works:**
1. Iterates over all images in `state["images"]`
2. For each image, constructs a prompt requesting a **15×15 grid analysis** (225 cells)
3. Uses the OpenRouter direct HTTP client (not LangChain — the model uses a custom response format)
4. Enforces `response_format: {"type": "json_object"}` for structured output
5. Each cell contains:
   - `items[]` — D&D items found in that cell
   - `ores[]` — predicted ores (depends on terrain)
   - `entities[]` — monsters/animals (depends on time + terrain)
   - `terrain` — biome classification
   - `prerequisites[]` — traversal requirements
   - `cell [x,y]` — coordinates
   - `description` — 2-line max flavor text
6. Parses the JSON, validates into `GridCell` Pydantic models
7. Updates `state["grid_data"]` and sets `needs_image_processing = False`

**Grid cell example:**
```json
{
  "items": [{"name": "Iron Sword", "category": "weapon"}],
  "ores": ["iron", "coal"],
  "entities": [{"name": "Goblin Scout", "type": "hostile", "count": 1}],
  "terrain": "mountains",
  "prerequisites": ["climbing gear", "torch"],
  "cell": [7, 3],
  "description": "A narrow mountain pass with exposed iron veins. A goblin watches from the shadows."
}
```

**15×15 grid rationale:** A 225-cell grid offers sufficient granularity to represent a D&D encounter area (∼150ft × 150ft at 10ft/cell) without overwhelming the model's output capacity.

---

### Node 3 — Re-Description Engine (Conditional)

**File:** `agents/node3_redescriptor.py`
**Model:** `openrouter/owl-alpha` (1M context window) via OpenRouter
**Trigger:** When time passes in-game and environmental descriptions need updating

**How it works:**
1. Receives previous grid data + a time change description
2. Sends to OWL-alpha (1M context — handles the full 225-cell grid easily)
3. The system prompt instructs the model to:
   - **Change entities** based on time (night → nocturnal/undead, day → diurnal animals)
   - **Keep items** static (loot doesn't despawn)
   - **Keep ores** unchanged (geology is stable)
   - **Update descriptions** for lighting/weather changes
4. Parses the returned JSON grid and merges into `state["grid_data"]`
5. Sets `needs_re_description = False`

**Why OWL-alpha:** With a 1M token context window, OWL-alpha can process the entire 225-cell grid in a single pass without chunking or losing coherence.

---

### Node 4 — Tool Agent (Reactive)

**File:** `agents/node4_tool_agent/agent.py` + `agents/node4_tool_agent/tools.py`
**Model:** `qwen/qwen3-coder:free` via OpenRouter
**Type:** Reactive tool-calling agent using LangChain's `create_agent`

**6 Tools:**

#### 1. `dice_roller(dice, count, advantage, disadvantage, modifier, reason)`
- Supports d4/d6/d8/d10/d12/d20/d100
- Advantage = roll twice take higher; Disadvantage = roll twice take lower
- Returns `DiceRoll` as JSON

#### 2. `damage_multiplier(base_damage, damage_type, monster_type, position_description, is_trapped, is_restrained, is_unconscious)`
- Elemental effectiveness table (fire melts ice, radiant destroys undead, etc.)
- Positional multipliers (buried under tree = 1.6×, stuck in hole = 1.3×, etc.)
- Compound multipliers: `total = base × elemental × position`
- Returns `DamageCalculation` as JSON

#### 3. `stats_multiplier_and_updater(current_stats_json, monster_name, exp_gained, monster_difficulty)`
- Built-in monster difficulty table (rat→10xp, dragon_ancient→15000xp)
- Level-up logic: level up when `exp >= exp_to_next`, increases caps and HP/MP
- Stat cap table: Level 1 max = 10, Level 10 max = 30
- Returns updated `CharacterStats` as JSON

#### 4. `skill_updater_and_validator(current_skills_json, action, skill_name, new_skill_json, sacrifice_skills)`
- Actions: `check_cooldowns`, `reduce_cooldowns`, `use_skill`, `add_skill`, `sacrifice_for_new`
- Sacrifice mechanic: combine skills → averaged level + name concatenation → new evolved skill
- Returns updated skills array as JSON

#### 5. `inventory_checker_and_updater(current_inventory_json, action, item_name, quantity, item_json, currency_amount)`
- Actions: `check`, `add`, `remove`, `use`, `check_currency`, `spend_currency`
- Currency-aware: tracks gold/silver/copper/platinum coins
- Validates sufficient quantity before allowing actions
- Returns updated inventory as JSON

#### 6. `json_data_maker_and_tracker(action, data_type, data_name, existing_data_json, new_data_json, relationship_entity, relationship_disposition, relationship_description)`
- Actions: `get`, `set`, `update_relationship`, `list_all`
- Manages arbitrary structured data: inventory records, relationships, quest states
- Relationship system: disposition -100 (hostile) to 100 (friendly), cumulative
- Returns updated data store as JSON

**Agent architecture:**
The tool agent uses LangChain's `create_agent` with `MemorySaver` checkpointer. The system prompt defines when to use each tool. The agent runs a tool-calling loop:
1. Reduces all skill cooldowns
2. Processes pending combat actions (dice → damage → stats)
3. Checks inventory for required items
4. Updates relationships and JSON data store
5. Returns a summary of all changes

---

### Node 5 — Context Injector (Main)

**File:** `agents/node5_context_injector.py`
**Model:** `nvidia/nemotron-3-super-120b-a12b:free` via OpenRouter
**Position:** First node in the pipeline (runs before any conditional or main node)

**How it works:**
1. Collects all available game state: prompt, input data, grid summaries, search results, tool history
2. Sends to Nemotron Super with a strict JSON response format
3. The model compresses everything into a `ContextSummary` object:
   ```json
   {
     "active_quests": ["Find the Lost Amulet"],
     "current_location": "Darkwood Forest",
     "party_members": ["Thorn Ironhand"],
     "recent_events": ["Defeated goblin patrol", "Found hidden cave"],
     "inventory_summary": {"weapon": 2, "potion": 5, "material": 12},
     "key_items": ["Ancient Map Fragment"],
     "time_of_day": "night",
     "weather": "foggy",
     "narrative_context": "The party stands at the mouth of a cave..."
   }
   ```
4. Stores in `state["context_summary"]` and merges into `state["game_data"]["context"]`

**Why Nemotron Super:** This 120B-parameter model excels at summarization and structured extraction while being available for free on OpenRouter. Its large parameter count ensures high-quality context preservation.

---

### Node 6 — Story Generator (Main)

**File:** `agents/node6_story_generator.py`
**Model:** `qwen/qwen3-coder:free` via OpenRouter
**Position:** After Node 4 (tool agent), before Node 7 (output)

**How it works:**
1. Aggregates: context summary, grid data, tool results (dice rolls, damage, stats), inventory, skills, character stats
2. Builds a rich prompt with all game mechanics data
3. The system prompt defines storytelling rules:
   - Second person POV ("You see...")
   - Under 500 words
   - Vivid environmental descriptions based on terrain/time
   - Natural incorporation of dice rolls and skill usage
   - Narrative hooks for the next turn
   - D&D 5e flavor
4. Invokes Qwen Coder with temperature 0.7 (creative but coherent)
5. Stores the narrative in `state["story_output"]`

---

### Node 7 — Output Pusher

**File:** `agents/node7_output_pusher.py`
**Position:** Final node — runs after story generation

**How it works:**
1. Constructs a `GameOutput` Pydantic model containing:
   - `uuid` — matches the request UUID
   - `game_data` — full game state (stats, inventory, skills, relationships, grid data)
   - `story` — the generated narrative
   - `context_summary` — the compressed context
   - `timestamp`
2. Calls `OutputCache.store_result()` which writes to Redis DB 1 with TTL
3. Sets `state["processed"] = True`

---

## 7. Model Configuration

All models are configured in `config/models.py` and controlled via `.env` variables:

| Node | Model | Provider | Via | Temperature | Max Tokens |
|------|-------|----------|-----|-------------|------------|
| Node 1 | `gemini-2.0-flash` | Google | `langchain-google-genai` | 0.3 | Default |
| Node 2 | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | OpenRouter | Direct HTTP | 0.1 | 8,192 |
| Node 3 | `openrouter/owl-alpha` | OpenRouter | Direct HTTP | 0.2 | 65,536 |
| Node 4 | `qwen/qwen3-coder:free` | OpenRouter | `langchain-openai` (compatible API) | 0.3 | 8,192 |
| Node 5 | `nvidia/nemotron-3-super-120b-a12b:free` | OpenRouter | Direct HTTP | 0.1 | 2,048 |
| Node 6 | `qwen/qwen3-coder:free` | OpenRouter | Direct HTTP | 0.7 | 8,192 |

**Why two API patterns?**
- Nodes 1 & 4 use **LangChain model wrappers** (`ChatGoogleGenerativeAI`, `ChatOpenAI` with OpenRouter base URL) because they need the agent/tool-calling loop that LangChain provides
- Nodes 2, 3, 5, 6 use a **direct HTTP client** (`utils/openrouter_client.py`) because they are simple prompt→response calls with no tool loops, giving us finer control over response_format and parameters

---

## 8. Multi-Tasking Engine

**File:** `engine/multi_tasker.py`

The `MultiTaskEngine` class implements concurrent request processing:

### Concurrency Model
```python
self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
```
- Each incoming request acquires the semaphore before processing
- Default max: 100 concurrent requests (configurable via `MAX_CONCURRENT_REQUESTS`)
- Uses `asyncio.create_task()` for non-blocking spawning
- Task completion callbacks automatically remove finished tasks from the active set

### Main Loop
```
while running:
    1. Check memory backpressure (every 100 requests)
    2. Pop next request from Redis input queue
    3. Acquire semaphore
    4. Create async task
    5. Track in active_tasks set
    6. Repeat (non-blocking)
```

### Memory Backpressure
```
Every 100 requests:
  ┌─────────────────────────────────────────┐
  │ Check Redis output DB memory %           │
  ├─────────────────────────────────────────┤
  │ If >= 90%:                                │
  │   Back off 3 seconds                      │
  │   Recheck memory                          │
  │   If still >= 90%: continue waiting       │
  │   If < 90%: resume accepting requests     │
  ├─────────────────────────────────────────┤
  │ If < 90%: continue normally               │
  │ Reset counter                             │
  └─────────────────────────────────────────┘
```

---

## 9. Throttling & Backpressure

The system has three layers of backpressure:

| Layer | Mechanism | Scope | Trigger |
|-------|-----------|-------|---------|
| **1. Concurrency cap** | `asyncio.Semaphore` | Per-request | Reaches `MAX_CONCURRENT_REQUESTS` (default 100) |
| **2. Memory monitoring** | Redis `INFO memory` check | Per-100-requests | Output DB memory > `OUTPUT_MEMORY_THRESHOLD` (default 90%) |
| **3. Empty queue backoff** | `await asyncio.sleep(0.1)` | Per-iteration | Input queue has no requests |

---

## 10. Edge Cases & Defensive Design

| # | Edge Case | Where Handled | Behavior |
|---|-----------|---------------|----------|
| 1 | **Empty input queue** | `multi_tasker.py` | 100ms sleep, retry |
| 2 | **Redis connection failure** | `redis/client.py` | `connect()` is idempotent; methods return `None`/`False` on failure |
| 3 | **Model API timeout** | Each node has `try/except` | Error message propagated in state; pipeline continues |
| 4 | **Memory pressure spike** | `multi_tasker.py` | Backs off 3s, rechecks, loops until under threshold |
| 5 | **No images to process** | `node2_image_processor.py` | Checks `state.get("images")`; returns immediately if empty |
| 6 | **No re-description data** | `node3_redescriptor.py` | Checks `state.get("re_description_data")`; returns immediately if missing |
| 7 | **Orphaned requests** | Redis TTL (configurable, default 1 hour) | Auto-expired from both input and output DBs |
| 8 | **Concurrent storm (100+ users)** | `asyncio.Semaphore` + active task tracking | Tasks queue up on the semaphore; processed as slots free |
| 9 | **State explosion (infinite growth)** | `node5_context_injector.py` | Context summarization caps narrative at 500 chars; uses accumulating reducers properly |
| 10 | **Grid parsing failure** | `node2_image_processor.py` | Catches JSON decode errors per-image; continues with remaining images |
| 11 | **Tool agent infinite loop** | LangChain recursion limit + tool retry policy | Each tool call has bounded execution |
| 12 | **Windows compatibility** | `main.py` signal handlers | Falls back to no-signal mode on Windows (where `add_signal_handler` is unavailable) |
| 13 | **Invalid dice type** | `tools.py:dice_roller` | Returns error JSON with description |
| 14 | **Inventory overflow** | Not enforced (expected — D&D has no hard cap) | Inventory grows unbounded; context injector summarizes counts |
| 15 | **Same UUID processed twice** | Not prevented (Redis get+delete is atomic per pop, but two server instances could race) | Last write wins in output DB; first write's TTL will clean up |

---

## 11. Setup & Running

### Prerequisites
- Python 3.10+
- Redis server (local or remote)
- OpenRouter API key (free tier works for most models)
- Google Gemini API key (for web search)

### Installation

```bash
# Navigate to project
cd rpg_ai_server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-your-key
GOOGLE_API_KEY=your-gemini-key

# Optional (shown with defaults)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_INPUT_DB=0
REDIS_OUTPUT_DB=1
REDIS_PASSWORD=
REDIS_TTL_SECONDS=3600
MAX_CONCURRENT_REQUESTS=100
OUTPUT_MEMORY_THRESHOLD=90.0
BACKOFF_SECONDS=3.0
LOG_LEVEL=INFO
```

### Running

```bash
# Start Redis (if local)
redis-server

# Run the AI server
python -m rpg_ai_server.main
```

### Testing

Push a test request to Redis DB 0:
```bash
redis-cli -n 0 SET "test-uuid-1" '{
  "uuid": "test-uuid-1",
  "prompt": "A warrior enters a dark forest. A goblin patrol approaches.",
  "data": {"character": {"name": "Thorn", "class": "Fighter", "level": 1}},
  "images": [],
  "timestamp": 1700000000.0
}' EX 3600
```

Read the result from Redis DB 1:
```bash
redis-cli -n 1 GET "test-uuid-1"
```

---

## 12. Configuration Reference

### `config/settings.py` — `Settings` dataclass tree

```
Settings
├── redis: RedisConfig
│   ├── host: str (default: localhost)
│   ├── port: int (default: 6379)
│   ├── input_db: int (default: 0)
│   ├── output_db: int (default: 1)
│   ├── password: Optional[str]
│   └── ttl_seconds: int (default: 3600)
│
├── models: ModelConfig
│   ├── gemini_model: str (default: gemini-2.0-flash)
│   ├── image_model: str (default: nvidia/nemotron-3-nano-omni...)
│   ├── redescription_model: str (default: openrouter/owl-alpha)
│   ├── tool_agent_model: str (default: qwen/qwen3-coder:free)
│   ├── context_injector_model: str (default: nvidia/nemotron-3-super...)
│   └── story_model: str (default: qwen/qwen3-coder:free)
│
└── app: AppConfig
    ├── max_concurrent_requests: int (default: 100)
    ├── output_memory_threshold: float (default: 90.0)
    ├── backoff_seconds: float (default: 3.0)
    ├── log_level: str (default: INFO)
    ├── openrouter_api_key: Optional[str]
    ├── openrouter_base_url: str (default: https://openrouter.ai/api/v1)
    └── google_api_key: Optional[str]
```

---

## Appendix A: LangGraph Concepts Used

| Concept | Where | Purpose |
|---------|-------|---------|
| `StateGraph` | `graph_builder.py` | Main graph construction |
| `TypedDict` state | `schemas/state.py` | Typed, shared state across all nodes |
| `Annotated[list, operator.add]` | `schemas/state.py` | Accumulating reducers for skills, inventory, tool results |
| `add_node()` | `graph_builder.py` | Registering all 7 nodes + router |
| `add_edge()` | `graph_builder.py` | Fixed edges (START→Node5, Node4→Node6→Node7→END) |
| `add_conditional_edges()` | `graph_builder.py` | Router decisions, loop-back logic |
| `command` | Not used (conditional edges suffice) | — |
| `Send` | Not used (concurrency handled by MultiTaskEngine) | — |
| `create_agent` | `node1_web_search.py`, `node4_tool_agent/agent.py` | Tool-calling agent loops |
| `MemorySaver` | `node4_tool_agent/agent.py` | Agent memory for tool-calling loop |

## Appendix B: OpenRouter Direct Client

**File:** `utils/openrouter_client.py`

The `OpenRouterDirectClient` wraps `httpx.AsyncClient` for direct API calls to OpenRouter:
- `chat_completion()` — generic chat completion with optional `response_format`
- `extract_json()` — convenience for JSON mode with system+user prompts
- Automatic header injection (API key, referer, title)
- 120-second timeout for long-context models (OWL-alpha)

This client is used by Nodes 2, 3, 5, and 6 because these nodes don't need LangChain's agent loop — they make single prompt→response calls with strict JSON output.

---

## Appendix C: Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Two Redis databases** | Input queue and output cache have different access patterns (FIFO pop vs keyed read) and different lifecycle requirements |
| **Conditional flags in state** | Allows the router to cleanly decide which nodes to execute without hardcoding flow logic |
| **Separate tool agent** | Game mechanics (dice, damage, stats, skills, inventory) are complex enough to warrant their own dedicated agent with 6 specialized tools |
| **Context injection as first node** | Ensures all downstream nodes have a compressed, summarized view of the game state, preventing token overflow |
| **Direct HTTP for most nodes** | LangChain wrappers add overhead; for simple prompt→response calls, direct HTTP is faster and more controllable |
| **asyncio Semaphore** | Simpler and more predictable than a thread pool; all operations are already async (HTTP calls, Redis calls) |
| **Memory check every 100 requests** | Balances monitoring overhead with responsiveness; 100 is configurable |
