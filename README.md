# RPG AI Quest — Open-World AI Game Engine
**NOTE**: This is a work in progress.
![Build Status](https://img.shields.io/badge/build-stable-brightgreen)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?logo=redis&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1E2A4A?style=flat)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

> **An async open-world RPG powered by a 7-node LangGraph AI pipeline and a Redis-backed architecture.**

---

## TL;DR — What is this?

An AI-driven **D&D-style game engine** where every action is processed by a multi-agent pipeline. Features a fully data-driven world (weapons, armor, spells, enemies, quests, NPCs, skills), dynamic weather, biome transitions, and a block-based world with Dijkstra pathfinding.

## System Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│   Browser    │◄───►│   Next.js    │◄───►│   Redis (Upstash)    │
│  (Client)    │ SSE │   Frontend   │     │  ┌────────────────┐  │
└──────────────┘     └──────────────┘     │  │  DB 0: Queue    │  │
                                          │  │  DB 1: State    │  │
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
| **FastAPI AI Server** | Processes game requests through a 7-node LangGraph pipeline | Python, FastAPI |
| **Redis (Upstash)** | Shared state, queues, and caching | 2 isolated databases |
| **Upstash Search** | Game memory / RAG — AI-hybrid retrieval of narrative history | Semantic + full-text, shared index filtered by sid |

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [RPG AI Server](#rpg-ai-server)
  - [7-Node LangGraph Pipeline](#7-node-langgraph-pipeline)
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
PLA- [Edge Cases & Defensive Design](#edge-cases--defensive-design)

---

## RPG AI Server

### 7-Node LangGraph Pipeline

```
START → Node5 (Context) → Router → [Node1/2/3 loops] → Node4 (Tools) → Node6 (Story) → Node7 (Output) → END
```

| Node | Role | Model | Trigger |
|------|------|-------|---------|
| **1** | 🔍 Web search for lore & rules | `gemini-2.0-flash` | `needs_search` |
| **2** | 🖼️ Image → 15×15 grid analysis | `nemotron-nano` | `needs_image_processing` |
| **3** | ♻️ Re-describe grid (time/narrative) | `owl-alpha` | `needs_re_description` |
| **4** | 🛠️ Tool agent (dice, combat, stats, inventory) | `qwen-coder` | Every turn |
| **5** | 📝 Context summarization | `nemotron-super` | Every turn |
| **6** | 📖 Story generation (2nd person, <500 words) | `qwen-coder` | Every turn |
| **7** | 📤 Push result to Redis DB 1 | — | Final |

### Data Flow

```
1. Client sends action → Next.js
2. Next.js pushes {uuid, prompt} → Redis DB 0 (input:queue)
3. FastAPI polls queue → loads game state from Redis DB 1
4. Runs through LangGraph pipeline → writes output to Redis DB 1
5. Next.js pushes result to client via Server-Sent Events (SSE)
6. Client merges delta into local state and renders UI
```

### Redis Layer

| Database | Purpose | Key Pattern | TTL |
|----------|---------|-------------|-----|
| **DB 0** | Input queue & coordination | `input:queue`, `trigger:busy` | — |
| **DB 1** | Game state + output cache | `games:{sid}:state`, `output:{sid}` | 1 hour |

**Key classes in `redis/client.py`:**
- `RedisClient` — base wrapper with `set_json`, `get_json`, `memory_percent()`
- `InputRedisClient` — `pop_request()` from DB 0
- `OutputRedisClient` — `push_result()` to DB 1

### Concurrency & Backpressure

| Layer | Mechanism | Threshold |
|-------|-----------|-----------|
| **Cap** | `asyncio.Semaphore` | 100 concurrent requests |
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

- Story/incident text is drained from game state on major events or every 10 actions
- Text is split into chunks (~512 tokens, overlap 32) and upserted to the **AI-hybrid search index** (`game-memory`); Upstash embeds server-side, no local model
- Games share one index, scoped by the `sid` field (content + metadata) with id prefix `{sid}:`
- Retrieval: build a text query from current context → `search(query, limit=top_k, filter="@metadata.sid = '<sid>'")` → inject top memories into the prompt as `PREVIOUS MEMORIES`
- Incident learning system classifies actions and tracks gain/loss patterns

**Scenario save slots (named memories):**
- Each scenario has a user-chosen name (client label) + uuid (the `sid` embedded in every memory document)
- Entry: found by uuid → continue live, or `/memory/restore` from the saved blob if Redis TTL expired; not found → fresh game
- Exit: Save (export via `fetch(prefix='{sid}:')`) or Don't save (optional wipe via delete filter) — documents survive unless explicitly deleted
- Autosave: every 10 messages (drain trigger) the client refreshes its local blob
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
4. Autosave: every 10 messages, drain fires → memory export blob refreshed (client-owned)
5. Exit: Save (export namespace) or Don't save (discard advances) — client-owned flow

**SSE Push Pattern:**
1. FastAPI calls `/api/games/worker` with `{uuid: sid}`
2. Next.js writes to open SSE connection for that session
3. No Redis polling — pure push-based event delivery

---

## Setup & Running

### Prerequisites

- Python 3.10+
- Redis server (or Upstash account)
- OpenRouter API key
- Google Gemini API key

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
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_INPUT_DB=0
REDIS_OUTPUT_DB=1
REDIS_TTL_SECONDS=3600

# Upstash Search (game memory)
UPSTASH_SEARCH_REST_URL=your-search-url
UPSTASH_SEARCH_REST_TOKEN=your-search-token
SEARCH_INDEX_NAME=game-memory
SEARCH_TOP_K=3

# OpenRouter API
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Google Gemini API
GOOGLE_API_KEY=your-google-gemini-key

# System Configuration
MAX_CONCURRENT_REQUESTS=100
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
# Push a test request to the input queue (DB 0)
redis-cli -n 0 SET test-uuid '{"prompt":"A goblin approaches...","sid":"test-session"}' EX 3600

# Read the result from the output cache (DB 1)
redis-cli -n 1 GET test-uuid
```

---

## Configuration Reference

### Model Configuration

| Node | Model | Provider | Temperature | Max Tokens |
|------|-------|----------|-------------|------------|
| **1 (Web Search)** | `gemini-2.0-flash` | Google | 0.3 | Default |
| **2 (Image)** | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | OpenRouter | 0.1 | 8,192 |
| **3 (Re-describe)** | `openrouter/owl-alpha` | OpenRouter | 0.2 | 65,536 |
| **4 (Tools)** | `qwen/qwen3-coder:free` | OpenRouter | 0.3 | 8,192 |
| **5 (Context)** | `nvidia/nemotron-3-super-120b-a12b:free` | OpenRouter | 0.1 | 2,048 |
| **6 (Story)** | `qwen/qwen3-coder:free` | OpenRouter | 0.7 | 8,192 |
| **7 (Output)** | — | — | — | — |

**API Patterns:**
- **LangChain wrappers** (Nodes 1, 4): For agent/tool-calling loops.
- **Direct HTTP** (Nodes 2, 3, 5, 6): Simpler prompt→response flow with finer control over `response_format`.

---

## Edge Cases & Defensive Design

| # | Edge Case | Handling |
|---|-----------|----------|
| 1 | Empty input queue | 100ms sleep, retry |
| 2 | Redis connection failure | Idempotent `connect()`, graceful failure |
| 3 | LLM API timeout | `try/except` per node, pipeline continues |
| 4 | Memory pressure spike | Back off 3s, recheck, loop |
| 5 | Orphaned requests | Redis TTL auto-expires (1h default) |
| 6 | Concurrent storm (100+) | Semaphore queues excess tasks |
| 7 | State explosion | Context summarization caps at 500 chars |
| 8 | Tool agent infinite loop | LangChain recursion limit + bounded execution; full loop-guard suite (router pass cap, tool-call limit, futile-action guard, `RemainingSteps` degradation) — see `plan/loops.md` |
| 9 | Invalid dice type | Returns structured error JSON |
| 10 | Duplicate UUID | Last-write-wins; TTL cleans up |