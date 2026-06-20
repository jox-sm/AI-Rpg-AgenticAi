# RPG AI Server — Redis API & System Architecture

## Overview

A single-file FastAPI server (`rpg_ai_server/redis_api.py`) that exposes Redis operations as HTTP endpoints. No imports from the agent, skill, or engine layers — pure Redis CRUD.

Run:

```
python -m uvicorn rpg_ai_server.redis_api:app --port 8000
```

---

## Redis Layer

Four logical databases via key prefixes (single Upstash or local Redis instance).

| Prefix | Client Class | Purpose |
|--------|-------------|---------|
| `input:` | `InputRedisClient` | Request queue, delayed retry, dead letter, worker heartbeats |
| `games:` | `GamesRedisClient` | Per-game state hashes, counters, distributed locks |
| `rag:` | `RagRedisClient` | RAG staging queue + chunk storage (separate Upstash instance optional) |
| `output:` | `OutputRedisClient` | LLM output cache with TTL |

All clients inherit from `RedisClient` which wraps `upstash_redis.AsyncRedis` (Upstash REST-based).

### Connection

- Lazily connects on first use via `_get_input()`, `_get_games()`, etc.
- Singletons stored as module-level globals (`_input`, `_games`, `_rag`, `_output`)
- On `startup` event: all four connect
- On `shutdown` event: all four disconnect

---

## API Endpoints

### Health

| Method | Path | Returns |
|--------|------|---------|
| `GET` | `/health` | `{"status": "ok"}` |

### Queue (input:)

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| `POST` | `/queue/push` | `uuid`, `data` (JSON string) | RPUSH to `input:queue` |
| `GET` | `/queue/pop` | — | LPOP from `input:queue` |
| `GET` | `/queue/length` | — | LLEN of `input:queue` |
| `POST` | `/queue/delayed/push` | body `item`, query `score` | ZADD to `input:queue:delayed` |
| `GET` | `/queue/delayed/pop` | `max_score` | ZRANGEBYSCORE + ZREMRANGEBYSCORE |
| `POST` | `/queue/dead/push` | body `item` | ZADD to `input:queue:dead` |

### Game State (games:)

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| `GET` | `/games/{uuid}/state` | — | HGETALL, JSON-decodes fields |
| `GET` | `/games/{uuid}/state/{field}` | — | HGET single field |
| `PUT` | `/games/{uuid}/state/{field}` | `value` | HSET a field |
| `DELETE` | `/games/{uuid}/state/{field}` | — | HDEL a field |
| `POST` | `/games/{uuid}/counter/incr` | — | INCR counter |
| `PUT` | `/games/{uuid}/counter` | `value` | SET counter |
| `GET` | `/games/{uuid}/lock` | `worker_id`, `ttl` | Acquire SET NX EX lock |
| `DELETE` | `/games/{uuid}/lock` | `worker_id` | Release lock (compare-and-delete) |
| `POST` | `/games/{uuid}/expire` | `ttl` | EXPIRE state hash |

### RAG Staging (rag:)

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| `POST` | `/rag/staging/push` | body `payload` | RPUSH to `rag:queue` |
| `GET` | `/rag/staging/pop` | — | LPOP from `rag:queue` |
| `GET` | `/rag/staging/count` | — | LLEN of `rag:queue` |
| `GET` | `/rag/chunk/{uuid}/{index}` | — | GET stored chunk |

### Output Cache (output:)

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| `GET` | `/output/{uuid}` | — | GET JSON |
| `PUT` | `/output/{uuid}` | body `data` | SET with TTL |
| `GET` | `/output/count` | — | Key count under prefix |

### General

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| `GET` | `/keys` | `pattern`, `prefix` | KEYS scoped to prefix |
| `GET` | `/dbsize` | `prefix` | Count keys (or sum across all) |
| `DELETE` | `/keys/{key}` | `prefix` | DEL single key |

---

## System Architecture

### Data Flow

```
Client (game request)
  │  POST /queue/push {uuid, prompt, data}
  ▼
Redis input:queue
  │
  ▼  (LPOP)
MultiTaskEngine
  │  asyncio.Semaphore(100)
  │  per-request: orchestrator.process_request(request)
  ▼
GameOrchestrator
  │  1. Acquire lock (games:{uuid}:lock)
  │  2. Load or build initial state (world gen, CharacterStats)
  │  3. compiled_graph.ainvoke(state)
  ▼
LangGraph Pipeline (7 nodes)
  │
  │  n5 ContextInjector (summarize state → ContextSummary)
  │    → Router (check boolean flags)
  │      → n1 WebSearch (Gemini, conditional)
  │      → n2 ImageProcessor (Nemotron, conditional)
  │      → n3 Redescriptor (OWL-alpha, conditional)
  │      → n4 ToolAgent (Qwen Coder, 13 tools)
  │    → n6 StoryGenerator (Qwen Coder)
  │    → n7 OutputPusher (serialize → output cache)
  │
  ▼
Redis output:{uuid}
  │
  └── try_drain() → RAG staging queue (rag:queue)
      at 10 actions or major events
```

### 7-Node LangGraph Pipeline

| Node | Model | Role |
|------|-------|------|
| n1 Web Search | Gemini 2.0 Flash (LangChain agent) | Search for lore/rules — conditional |
| n2 Image Processor | Nemotron Nano 30B (direct HTTP) | Images → 15×15 grid — conditional |
| n3 Redescriptor | OWL-alpha (direct HTTP) | Re-describe grid for time changes — conditional |
| n4 Tool Agent | Qwen Coder (LangChain agent) | Dice, damage, stats, inventory, skills, crafting |
| n5 Context Injector | Nemotron Super 120B (direct HTTP) | Always-first: distill state → ContextSummary |
| n6 Story Generator | Qwen Coder (direct HTTP) | Narrative prose from tool results + context |
| n7 Output Pusher | — (pure Python) | Serialize GameOutput → Redis output cache |

### Tools (node4_tool_agent)

13 tools across 8 modules in `tool_defs/`:

| Tool | Source | Purpose |
|------|--------|---------|
| `situational_dice` | `dice_tools.py` | Recommend dice config from power vs plan analysis |
| `dice_roller` | `dice_tools.py` | Roll d4–d100 with advantage |
| `damage_multiplier` | `combat_tools.py` | Elemental + position + status damage calc |
| `stats_multiplier_and_updater` | `stat_tools.py` | XP, level-ups, stat progression |
| `skill_updater_and_validator` | `stat_tools.py` | Cooldowns, skill add/sacrifice/evolution |
| `inventory_checker_and_updater` | `inventory_tools.py` | Add/remove/check items, load, currency |
| `json_data_maker_and_tracker` | `data_tools.py` | Persist quests, relationships, notes |
| `use_skill` | `skill_tools.py` | Execute any registered skill handler |
| `craft_with_choice` | `mastery_tools.py` | Location-aware worker hiring vs self-craft |
| `list_available_workers` | `mastery_tools.py` | Workers at location, optional skill filter |
| `check_mastery` | `mastery_tools.py` | Mastery rates per skill + available workers |
| `rarity_enhancer` | `rarity_tools.py` | Rarity tier upgrades with modifiers |

### Skills System

52 skill handlers across 11 categories, all registered in `SKILL_REGISTRY` dict:

| Module | Skills | Mastery Key |
|--------|--------|-------------|
| `combat_offense.py` | slash, pierce, bludgeon, power_attack, cleave | `combat_offense` |
| `combat_defense.py` | block, parry, dodge, shield_wall | `combat_defense` |
| `weapons.py` | sword, spear, hammer, archery, dual_wield | `weapons` |
| `magic.py` | spellcasting, mana_control, fire, ice, lightning | `magic` |
| `social.py` | persuasion, diplomacy, intimidate, deceive, bargain | `social` |
| `stealth.py` | stealth, sleight_of_hand, lockpick, pickpocket | `stealth` |
| `crafting.py` | smithing, alchemy, woodworking, enchanting | `smithing`/`alchemy`/etc. |
| `survival.py` | tracking, hunting, foraging, skinning | `survival` |
| `knowledge.py` | lore, arcana, history, medicine, healing, investigation, recipes | `knowledge` |
| `physical.py` | athletics, acrobatics, endurance, reflexes, climbing | `physical` |
| `strategy.py` | tactics, strategy, leadership, planning | `strategy` |

Every handler uses `success_check()` with a `mastery_key` parameter. This routes through the **mastery system** instead of D20:

```
rate = 1 - exp(-(level - 1) / scaling_factor)
effective_rate = (rate / difficulty_mult) × (1 + stat_bonus × 0.02)
```

### Game Mechanics Scripts

| Script | Lines | Purpose |
|--------|-------|---------|
| `dice_engine.py` | 120 | Dice rolls, advantage, success probability, catch mechanic |
| `combat_system.py` | 528 | Damage matrix (13 types × 12 targets), status effects, full combat turn |
| `strategy_damage.py` | 565 | Environmental hazards, amplifiers, chain reactions, escape DC |
| `incident_learning.py` | 415 | Action classification, diminishing returns stat/skill gains |
| `world_generator.py` | 241 | 6×6 seeded grid, biome adjacency, cell population |
| `mastery_formula.py` | 89 | Exponential formula engine, quality/difficulty helpers |

### Items Database

54 JSON files at `D:\AI agent\items-db\`, loaded by `ItemsDB` singleton (`utils/items_db.py`):

- `mastery.json` — 18 skill mastery tables with per-skill scaling/min/max/difficulty mods
- `workers.json` — 15 NPC workers with id, name, station, locations, mastery map, cost, personality
- 52 other files: weapons, armor, potions, enemies, NPCs, biomes, recipes, materials, spells, quests, etc.

ItemsDB guards against non-list JSON roots (`if not isinstance(items, list): continue`), so `mastery.json` and other object-root files are silently skipped. Search uses bigram cosine similarity + Damerau-Levenshtein re-rank.

### Queue & Lock Mechanics

- **Queue:** RPUSH/LPOP FIFO; delayed ZADD with exponential backoff (`5 × 2^n` seconds); max 3 retries then dead letter
- **Lock:** SET NX EX 30s; compare-and-delete on release; auto-expires on crash
- **Drain:** Every 10 actions or on death/level_up/quest_complete/boss_kill/new_biome → gzip story → push to RAG staging → reset counter
- **Backpressure:** Memory check every 100 requests; at 90%+ usage, back off 3s

### Worker System

15 hireable NPCs, each with their own mastery levels independent of the player. Key mechanics:

- Workers are available only at specific locations (bidirectional substring match)
- Hiring costs gold (`cost_per_attempt × difficulty_mult`)
- Worker mastery checks use `utils/mastery.py` `mastery_check()`, same formula as player but with the worker's level
- `craft_with_choice` tool offers three flows: hire worker → use worker's mastery; craft yourself → use player's mastery; no workers → auto-self

### Concurrency

- `asyncio.Semaphore(100)` limits concurrent in-flight requests
- Distributed Redis lock prevents duplicate processing across workers
- Graceful shutdown awaits all active tasks

---

## Files

| Path | Role |
|------|------|
| `rpg_ai_server/redis_api.py` | FastAPI Redis server (304 lines) |
| `rpg_ai_server/redis/client.py` | Base + 4 client classes (284 lines) |
| `rpg_ai_server/redis/game_state.py` | GameStateManager (72 lines) |
| `rpg_ai_server/redis/queue.py` | QueueManager (83 lines) |
| `rpg_ai_server/redis/rag_cache.py` | RagCache wrapper (32 lines) |
| `rpg_ai_server/config/settings.py` | RedisConfig + ModelConfig + AppConfig |
| `rpg_ai_server/engine/orchestrator.py` | Game lifecycle (157 lines) |
| `rpg_ai_server/engine/multi_tasker.py` | Concurrent drain loop (134 lines) |
| `rpg_ai_server/engine/graph_builder.py` | LangGraph StateGraph (115 lines) |
| `rpg_ai_server/schemas/types.py` | Pydantic models (150 lines) |
| `rpg_ai_server/schemas/state.py` | GameState TypedDict (43 lines) |
| `rpg_ai_server/agents/node4_tool_agent/agent.py` | LangChain agent (174 lines) |
| `rpg_ai_server/agents/node4_tool_agent/tool_defs/` | 9 tool modules |
| `rpg_ai_server/skills/` | 11 modules, 52 handlers |
| `rpg_ai_server/utils/items_db.py` | ItemsDB (261 lines) |
| `rpg_ai_server/utils/mastery.py` | Mastery system (108 lines) |
| `rpg_ai_server/utils/worker_manager.py` | Worker system (149 lines) |
| `rpg_ai_server/utils/swarm_helper.py` | Batch processing (144 lines) |
| `rpg_ai_server/scripts/` | 6 game mechanics scripts |
| `items-db/` | 54 JSON files (game data) |
