# RPG AI Quest — Open-World AI Game Engine
**NOTE**: This is a work in progress.
![Build Status](https://img.shields.io/badge/build-stable-brightgreen)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?logo=redis&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1E2A4A?style=flat)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

> **An async open-world RPG powered by a LangGraph v2 react pipeline and a Redis-backed architecture.**

---

## TL;DR — What is this?

An AI-driven **D&D-style game engine** where every action is processed by a multi-agent pipeline. Features a fully data-driven world (weapons, armor, spells, enemies, quests, NPCs, skills), dynamic weather, biome transitions, and a block-based world with Dijkstra pathfinding.

## System Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│   Browser    │◄───►│   Next.js    │◄───►│   Redis (Upstash)    │
│  (Client)    │ SSE │   Frontend   │     │  single REST instance│
└──────────────┘     └──────────────┘     │  prefixes: input: /  │
                                          │  output: / games:    │
                                          │  └────────────────┘  │
                                          └──────────┬───────────┘
                                                     │
                                          ┌──────────▼───────────┐
                                          │  FastAPI AI Server   │
                                          │  (Python + LangGraph)│
                                          └──────────┬───────────┘
                                                     │
┌──────────▼───────────┐
                                           │  Upstash Search      │
                                           │  (game memory / RAG) │
                                           └──────────────────────┘
```

| Component | Role | Tech |
|-----------|------|------|
| **Next.js Frontend** | HTTP/SSE client connections, game sessions, UI rendering | Next.js 16, TypeScript |
| **FastAPI AI Server** | Processes game requests through the LangGraph v2 react pipeline | Python, FastAPI |
| **Redis (Upstash)** | Shared state, queues, and caching | Single Upstash REST instance (`input:`/`output:`/`games:` prefixes) |
| **Upstash Search** | Game memory / RAG — AI-hybrid retrieval of narrative history | Semantic + full-text, shared index filtered by sid |

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [RPG AI Server](#rpg-ai-server)
  - [LangGraph v2 Pipeline](#langgraph-v2-pipeline)
  - [Data Flow](#data-flow)
  - [Redis Layer](#redis-layer)
  - [Concurrency & Backpressure](#concurrency--backpressure)
- [World System](#world-system)
  - [Block-Based Grid](#block-based-grid)
  - [Biome System](#biome-system)
- [Entity System](#entity-system)
- [Item & Equipment System](#item--equipment-system)
- [Skills & Progression](#skills--progression)
- [Game Mechanics](#game-mechanics)
- [RAG & Memory System](#rag--memory-system)
- [Frontend Integration (Next.js)](#frontend-integration-nextjs)
- [Setup & Running](#setup--running)
- [Configuration Reference](#configuration-reference)
- [Edge Cases & Defensive Design](#edge-cases--defensive-design)

---

## RPG AI Server

### LangGraph v2 Pipeline

```
START → classifier → react_router ⇄ {search|image|redescribe} → mechanics (6-way parallel fan-out) → context_refresh → summarizer → story → pusher → END
```

| Node | Role | Model | Trigger |
|------|------|-------|---------|
| **classifier** | Intent + flag classification (search/image/redescribe/mechanics) | `liquid/lfm-2.5-2.6b:free` | Every turn (entry) |
| **search (ex-Node1)** | Scrapy lore scrape (httpx + Scrapy Selector, no Gemini/LLM) | — | `needs_search` |
| **image (ex-Node2)** | Image → 15×15 grid analysis | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | `needs_image_processing` |
| **redescribe (ex-Node3)** | Re-describe grid (time/narrative) | `google/gemma-4-26b-a4b-it:free` | `needs_re_description` |
| **mechanics (ex-Node4)** | Parallel pure mechanics fan-out (dice/damage/stats/skill/inventory/json, no LLM agent loop) | — | Every turn |
| **summarizer (ex-Node5)** | Context summarization | `google/gemma-4-31b-it:free` | Every turn |
| **story (ex-Node6)** | Story generation (2nd person, <500 words) | `qwen/qwen3.8-27b:free` | Every turn |
| **pusher (ex-Node7)** | Push result to `output:` prefix | — | Final |

ReAct router is re-entrant (search/image/redescribe loop back to the router) with a max of 3 passes (`ROUTER_MAX_PASSES`), then forces `story`.

### Data Flow

```
1. Client sends action → Next.js
2. Next.js pushes {uuid, prompt} → single Upstash instance, `input:queue`
3. FastAPI polls queue → loads game state (`games:` prefix)
4. Runs through LangGraph v2 pipeline → writes output (`output:` prefix)
5. Next.js pushes result to client via Server-Sent Events (SSE)
6. Client merges delta into local state and renders UI
```

### Redis Layer

Single Upstash REST instance (`UPSTASH_REDIS_REST_URL/TOKEN`), namespaced by key prefix — no separate DB numbers.

| Prefix | Purpose | Key Pattern | TTL |
|----------|---------|-------------|-----|
| **`input:`** | Input queue & coordination | `input:queue`, `input:queue:delayed`, `input:queue:dead`, `input:workers:{id}:heartbeat` | — |
| **`output:`** | Output cache | `output:{sid}` | 1 hour |
| **`games:`** | Game state + counters + locks | `games:{sid}:state`, `games:{sid}:counter`, `games:{sid}:lock` | 1 hour |

**Key classes in `redis/client.py`:**
- `RedisClient` — base wrapper with `set_json`, `get_json`, `memory_percent()`
- `InputRedisClient` (`prefix="input"`) — `pop_request()` from `input:queue`
- `OutputRedisClient` (`prefix="output"`) — `push_result()` to `output:{sid}`
- `GamesRedisClient` (`prefix="games"`) — state hashes, counters, locks (`hset`/`hgetall`, `acquire_lock`/`release_lock`, `touch_game_keys`)

### Concurrency & Backpressure

| Layer | Mechanism | Threshold |
|-------|-----------|-----------|
| **Cap** | `asyncio.Semaphore` (`MAX_CONCURRENT_REQUESTS`) | 16 concurrent requests |
| **Deadline** | Per-request timeout (`REQUEST_TIMEOUT_SECONDS`) | 60s |
| **Router** | ReAct router passes (`ROUTER_MAX_PASSES`) | 3 passes, then force `story` |
| **Memory** | Redis `INFO memory` | >90% → 3s backoff |
| **Idle** | `await asyncio.sleep(0.1)` | No items in queue |

---

## World System

### Block-Based Grid

The world is a **weighted graph** of blocks, where every block is an interactive node:

- **Position:** `(x, y, depth)` — 2D coordinates with depth for elevation/underground
- **Biome:** Plain, Volcano, Snow Forest, Deepslate, Savanna
- **Weight:** Grass=1, Stone=1.2, Gravel=1.5, Lava=200 (with fire resistance)
- **Durability:** Current/max HP, mining threshold
- **Physics:** Temperature, wetness, elemental resistances, melt temperature
- **Traps:** Hidden holes, quicksand, ice lakes with trigger conditions

**Pathfinding:** Dijkstra on a weighted graph with **fuzzy logic** for biome transitions.

### Biome System

| Biome | Temp | Wetness | Resources | Hazards |
|-------|------|-------- |-----------|---------|
| **Plain** | 20-35°C | 30-50 | Wheat, herbs, clay | None |
| **Volcano** | 80-200°C | 0-10 | Obsidian, sulfur | Lava, toxic fumes, heat damage |
| **Snow Forest** | -20-5°C | 40-70 | Ice crystals, frostwood | Frostbite, blizzards, hypothermia |
| **Deepslate** | 5-15°C | 60-90 | Darkstone, rare ores | Cave-ins, poison gas |
| **Savanna** | 30-50°C | 5-20 | Cactus, sunstone | Quicksand, dehydration, sandstorms |

---

## Entity System

### 👤 Player
Controls a character with full D&D stats: health, hunger, thirst, stamina, equipment, skills, karma, sleep, and more. Player data includes a full equipment grid, rune sockets, skill levels, perks, and status effects.

### 🐺 Mobs & Monsters
- **Passive mobs:** Cows, pigs, rabbits, sheep, chickens, horses (herd behavior, tamable)
- **Monsters:** Skeletons, goblins, cave crawlers, spiders, wolves, watchers (aggression, pack AI)
- **Bosses:** Elite enemies with phase triggers, arenas, unique loot tables

### 🏠 NPCs & Workers
- **Merchants:** General goods, weapons, armor, magic, food
- **Quest Givers:** Leaders, mystics, guards, nobles
- **Workers:** Blacksmiths, farmers, builders with professions and specializations

### 👻 Special Characters & Hallucinations
Tied to **player karma**. At critically low stats, players may see ghost feasts, water mirages, and shadow figures.

| Entity | Trigger | Effect |
|--------|---------|--------|
| **Death** | 0.01% chance on any action | Instant kill |
| **Shadow** | Player has items | Demands item; 50% HP damage on refusal |
| **Ghosts** | Low karma zone | Stat debuffs |

---

## Item & Equipment System

### Item Categories (15 Total)

| # | Category | Example Items |
|---|----------|---------------|
| 1 | **Functional Blocks** | Furnaces, alchemist labs |
| 2 | **Furniture Blocks** | Chairs, tables, bookshelves |
| 3 | **Consumables** | Potions, food, drink |
| 4 | **Weapons** | Swords, bows, staves, daggers |
| 5 | **Armor** | Chestplates, shields, cloaks |
| 6 | **Clothing** | Robes, rings, amulets |
| 7 | **Ruined Materials** | Broken items, recyclable scraps |
| 8 | **Agriculture** | Crops, seeds, fertilizer |
| 9 | **Minerals** | Raw ores (iron, copper, gold) |
| 10 | **Alloys** | Smelted ingots, refined materials |
| 11 | **Entity Loot** | Monster drops, body parts |
| 12 | **Special Materials**| Dragon scales, void essence |
| 13 | **User Inventions**| Player-created items |
| 14 | **Runes** | Socketable modifiers |
| 15 | **Enchantment Scrolls**| Enchantment recipes |

### Rune Socketing (10 Types)

| Rune | Slot | Effect |
|------|------|--------|
| **Flame** | Weapon | Fire damage on hit |
| **Frost** | Weapon | Slow + cold damage |
| **Venom** | Weapon | Poison DoT |
| **Void** | Weapon | Armor penetration |
| **Soul** | Weapon | XP bonus |
| **Echo** | Weapon | Cooldown reduction |
| **Life** | Armor | Health regen |
| **Iron** | Armor | Defense boost |
| **Swift** | Armor | Speed boost |
| **Ward** | Armor | Elemental resistance |

---

## Skills & Progression

### Skill Categories (11 Total)

DAGGER
| Category | Skills |
|----------|--------|
| **Combat Offense** | Slash, pierce, bludgeon, power attack, cleave |
| **Combat Defense** | Block, parry, dodge, shield wall |
| **Magic** | Spellcasting, mana control, elemental magic |
| **Crafting** | Smithing, alchemy, woodworking, enchanting |
| **Knowledge** | Lore, arcana, history, medicine |
| **Physical** | Athletics, acrobatics, endurance, climbing |
| **Social** | Persuasion, diplomacy, intimidate, deceive |
| **Stealth** | Stealth, sleight of hand, lockpick |
| **Survival** | Tracking, hunting, foraging, skinning |
| **Weapons** | Sword/spear/hammer mastery, archery |
| **Strategy** | Tactics, leadership, planning |

### Level Scaling

| Level | XP to Next | Stat Points | Skill Points |
|-------|------------|-------------|--------------|
| 1 | 100 | 0 | 0 |
| 5 | 1,000 | 3 | 2 |
| 10 | 3,000 | 5 | 3 |
| 15 | 6,000 | 5 | 3 |
| 20 | 10,000 | 5 | 3 |

---

## Game Mechanics

### Dice Engine
- Standard dice: **d4, d6, d8, d10, d12, d20, d100**
- **Advantage/Disadvantage** rolling
- Configurable DC success checks and probability calculations

### Combat System
- Elemental damage × resistance modifiers
- Multipliers for positional, elemental, and status effects
- Hit location rolling, dodge/block/armor resolution
- Status effects: poison, fire, slow, stun

### Crafting System
Multi-category crafting with worker support and a full recipe database.
- **Smithing:** Metal weapons and armor
- **Alchemy:** Potions, poisons, elixirs
- **Woodworking:** Bows, staves, furniture
- **Enchanting:** Magic item creation

---

## RAG & Memory System

Narrative memory lives in **Upstash Search** (separate from Redis — Upstash Redis has no vector/AI search).

- Story/incident text is drained from game state on major events or every 25 actions (`DRAIN_THRESHOLD`)
- Text is split into chunks (~512 tokens, overlap 32) and upserted to the **AI-hybrid search index** (`game-memory`); Upstash embeds server-side, no local model
- Games share one index, scoped by the `sid` field (content + metadata) with id prefix `{sid}:`
- Retrieval: build a text query from current context → `search(query, limit=top_k, filter="@metadata.sid = '<sid>'")` → inject top memories into the prompt as `PREVIOUS MEMORIES`
- Incident learning system classifies actions and tracks gain/loss patterns

**Scenario save slots (named memories):**
- Each scenario has a user-chosen name (client label) + uuid (the `sid` embedded in every memory document)
- Entry: found by uuid → continue live, or `/memory/restore` from the saved blob if Redis TTL expired; not found → fresh game
- Exit: Save (export via `fetch(prefix='{sid}:')`) or Don't save (optional wipe via delete filter) — documents survive unless explicitly deleted
- Autosave: every 25 messages (drain trigger) the client refreshes its local blob
- Client-side flow (registry, popups) is owned by the fullstack folder — see `REDIS_API.md` "Scenario Lifecycle" for the server contract

---

## Frontend Integration (Next.js)

| # | File | Purpose |
|---|------|---------|
| 1 | `lib/ai-redis.ts` | Redis client (Upstash) |
| 2 | `lib/game-trigger.ts` | Trigger logic (queue ≥5 or 1s) |
| 3 | `app/api/games/[uuid]/play/route.ts` | Player action endpoint |
| 4 | `app/api/games/[uuid]/stream/route.ts` | SSE endpoint |
| 5 | `app/api/games/worker/route.ts` | FastAPI callback handler |
| 6 | `hooks/useGamePlay.ts` | Client-side React hook |
| 7 | `types/play.ts` | TypeScript types |

**Session lifecycle:**
1. New scenario: generate `sid` (uuid), write initial state to Redis; memory starts filling on first drain
2. Existing scenario: found → load from Redis (or `/memory/restore` from the saved blob if expired); not found → new game
3. TTL refresh on every action (1 hour timeout)
4. Autosave: every 25 messages, drain fires → memory export blob refreshed (client-owned)
5. Exit: Save (export namespace) or Don't save (discard advances) — client-owned flow

**SSE Push Pattern:**
1. FastAPI calls `/api/games/worker` with `{uuid: sid}`
2. Next.js writes to open SSE connection for that session
3. No Redis polling — pure push-based event delivery

---

## Setup & Running

### Prerequisites

- Python 3.10+
- Upstash Redis REST instance (`UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN`)
- OpenRouter API key (`OPENROUTER_API_KEY`, all LLM calls are OpenRouter-only)
- Optional: Upstash Search pair (`UPSTASH_SEARCH_REST_URL` + `UPSTASH_SEARCH_REST_TOKEN`) for game memory/RAG

### Installation

```bash
# 1. Clone the repo
cd rpg_ai_server

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```bash
# Single Upstash Redis REST instance (prefixes input:/output:/games:)
UPSTASH_REDIS_REST_URL=your-upstash-url
UPSTASH_REDIS_REST_TOKEN=your-upstash-token
REDIS_TTL_SECONDS=3600

# Upstash Search (game memory)
UPSTASH_SEARCH_REST_URL=your-search-url
UPSTASH_SEARCH_REST_TOKEN=your-search-token
SEARCH_INDEX_NAME=game-memory
SEARCH_TOP_K=3

# OpenRouter API (all LLM calls; no Gemini key needed)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# System Configuration
MAX_CONCURRENT_REQUESTS=16
REQUEST_TIMEOUT_SECONDS=60.0
ROUTER_MAX_PASSES=3
DRAIN_THRESHOLD=25
OUTPUT_MEMORY_THRESHOLD=90.0
BACKOFF_SECONDS=3.0
LOG_LEVEL=INFO
```

### Running

```bash
# Start Redis (if local)
redis-server

# Start the AI server
python -m rpg_ai_server.main
```

### Testing

```bash
# Push a test request to the input queue (input: prefix)
# (use the Upstash dashboard or REST client against key `input:queue`)

# Read the result from the output cache (output: prefix, key `output:{sid}`)
```

---

## Configuration Reference

### Model Configuration

All LLM calls go through OpenRouter only (no Gemini API key).

| Node | Model | Provider | Temperature | Max Tokens |
|------|-------|----------|-------------|------------|
| **classifier** | `liquid/lfm-2.5-2.6b:free` | OpenRouter | 0.3 | Default |
| **search (ex-Node1)** | — (Scrapy lore scrape, no LLM) | — | — | — |
| **image** | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | OpenRouter | 0.1 | 8,192 |
| **redescribe** | `google/gemma-4-26b-a4b-it:free` | OpenRouter | 0.2 | 65,536 |
| **mechanics (ex-Node4)** | — (parallel pure mechanics, no LLM agent loop) | — | — | — |
| **summarizer (context)** | `google/gemma-4-31b-it:free` | OpenRouter | 0.1 | 2,048 |
| **tool + story** | `qwen/qwen3.8-27b:free` | OpenRouter | tool 0.3 / story 0.7 | 8,192 |
| **pusher** | — | — | — | — |

**API Patterns:**
- **Scrapy tool** (search): httpx fetch + Scrapy Selector parsing, no LLM call.
- **Pure functions** (mechanics): 6-way `asyncio.gather` fan-out with deterministic merge, no LLM agent loop (legacy `node4_tool_agent` LangChain agent is unwired in v2).
- **Direct OpenRouter HTTP** (classifier/image/redescribe/summarizer/story): prompt→response flow with finer control over `response_format`.

---

## Edge Cases & Defensive Design

| # | Edge Case | Handling |
|---|-----------|----------|
| 1 | Empty input queue | 100ms sleep, retry |
| 2 | Redis connection failure | Idempotent `connect()`, graceful failure |
| 3 | LLM API timeout | `try/except` per node, pipeline continues |
| 4 | Memory pressure spike | Back off 3s, recheck, loop |
| 5 | Orphaned requests | Redis TTL auto-expires (1h default) |
| 6 | Concurrent storm (16+) | Semaphore queues excess tasks |
| 7 | State explosion | Context summarization caps at 500 chars |
| 8 | Tool agent infinite loop | LangChain recursion limit + bounded execution; full loop-guard suite (router pass cap, tool-call limit, futile-action guard, `RemainingSteps` degradation) — see `plan/loops.md` |
| 9 | Invalid dice type | Returns structured error JSON |
| 10 | Duplicate UUID | Last-write-wins; TTL cleans up |