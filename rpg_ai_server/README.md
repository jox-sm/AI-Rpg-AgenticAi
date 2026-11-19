# D&D RPG AI Server

An async D&D RPG AI server built with **LangGraph** and **LangChain**, **OpenRouter-only** for all LLM calls. Processes game requests via a single Upstash Redis (prefix-separated queues) through a v2 LangGraph pipeline and returns generated narratives.

## Quick Start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # add your API keys (placeholders only — never commit secrets)
```

## Running (AI server ↔ DeepSlate Dungeons)

The API and the engine can run either as one process or as two:

```bash
# Option A — one process: gameplay API + engine in the same uvicorn app
python -m uvicorn rpg_ai_server.api:app --port 8000

# Option B — two processes sharing Upstash Redis
python -m rpg_ai_server.main                                   # engine worker
python -m uvicorn rpg_ai_server.redis_api:app --port 8000      # FastAPI surface
```

Run exactly **one** engine (Option A, or one engine in Option B) — per-game
Redis locks keep a second engine safe, but it would waste model calls. Use
Option B when a test/lint pass wants the API without the engine tunneling to
OpenRouter.

```bash
# Option C — Docker (this repo; see ../docker-compose.yml for the web too)
docker build -t rpg-ai-server .
docker run --env-file rpg_ai_server/.env -p 8000:8000 rpg-ai-server
# memory/saves endpoints additionally need UPSTASH_SEARCH_REST_URL/_TOKEN
```

Web ↔ AI wiring:
- Web (`D:\deepslate dungeons`) relays browser traffic server-side via `/api/ai-server/[...path]`
  (`AI_SERVER_URL`, default `http://127.0.0.1:8000`) — no CORS needed on the FastAPI app.
  The relay is Clerk-session-gated and allowlists only the gameplay endpoints
  (queue push/length, output get/count, per-field state get/put, counter incr,
  memory, health, trigger probe).
- Web → AI turn payload is a `GameRequest` (`{uuid, prompt, data, images, timestamp}`; `sid` alias OK).
- Sessions started from a game page inject a `world_seed` (= catalog game id) and a
  `campaign` payload (characters/maps/items) into turn 1's
  `data` — see `REDIS_API.md` → "Session Seeding from a Catalog Game".
- Web → AI memory via `/api/games/[id]/memory` → AI `/memory/*` (Upstash Search).

## Architecture (v2 Pipeline)

```
Upstash Redis (prefix input:) → MultiTaskEngine → LangGraph v2 graph → Upstash Redis (prefix output:, games:)
```

| Stage | Role | Model | Type |
|------|------|-------|------|
| **Classifier** | Intent + routing flags (deterministic fast-path, then LLM) | `liquid/lfm-2.5-2.6b:free` (OpenRouter-only) | Entry |
| **React router** | Re-entrant `search\|image\|redescribe\|mechanics\|story` w/ budget terminators (≤3 passes, ≤12 LLM calls, 60s deadline) | — | Router |
| **Search** | Scrapy lore scrape over SRD sources (httpx + `scrapy.Selector`, no Google key) | — | Conditional |
| **Image** | Image → 15×15 grid analysis | Nemotron Nano (OpenRouter) | Conditional |
| **Redescribe** | Re-describe grid (time change) | `google/gemma-4-26b-a4b-it:free` (OpenRouter) | Conditional |
| **Mechanics** | 6 parallel pure sub-nodes: dice, damage, stats, skill, inventory, json (snapshot fan-out, ordered merge) | — (pure code, no LLM) | Parallel |
| **Context refresh** | Rolling `context` string update (cheap, no LLM) | — | Pure |
| **Summarizer** | Context summarization | `google/gemma-4-31b-it:free` (OpenRouter) | Main |
| **Story** | Story generation | `google/gemma-4-31b-it:free` (OpenRouter; qwen-27b free slug retired by OpenRouter) | Main |
| **Pusher** | Push result → Upstash `output:` prefix | — | Final |

**Flow:** `START → classifier → react_router ⇄ {search | image | redescribe} → mechanics → context_refresh → summarizer → story → pusher → END`

## Project Structure

```
rpg_ai_server/
├── config/          Environment & model config (settings.py, models.py)
├── schemas/         Pydantic models, enums, LangGraph state
├── redis/           Queue + game state + vector memory (single Upstash, prefixes input:/output:/games:)
├── agents/          classifier.py, node1–node7 modules, node4_parallel.py (6 pure sub-nodes)
├── engine/          graph_v2.py, graph builder, orchestrator, multi-tasker, bootstrap
├── utils/           Logger, OpenRouter HTTP client
├── tests/           Hard-test files (graph v2, orchestrator, atomic redis/engine, loops)
├── redis_api.py     FastAPI gameplay routes (API-only mode; routes live on an APIRouter)
├── api.py           Combined service app (gameplay API + in-process engine)
└── main.py          Engine-only entry point
```

## Key Features

- **Async multi-tasking** — up to 16 concurrent requests via `asyncio.Semaphore`
- **Memory backpressure** — checks Redis output memory every 100 requests; waits 3s if >90%
- **6 pure mechanics sub-nodes** — dice roller, damage, stats, skills (cooldown tick), inventory, JSON notes; snapshot fan-out, deterministic merge
- **All models OpenRouter-only** — no Gemini SDK, no Google key; Node1 lore uses Scrapy over SRD sources
- **Rolling memory** — `context` string (8000 chars) + `chat_log` (40 turns); story-buffer drain to vector memory every 25 turns
- **1-hour TTL** — requests/results auto-expire

## Configuration

Set in `.env`: `OPENROUTER_API_KEY`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, model names, `SCRAPER_*`, concurrency/memory/loop-guard limits. `REDIS_HOST`/`PORT`/`DBs` remain only as an unused local fallback. (Node1 uses Scrapy — no Google key needed.)

## How it Works

1. Frontend pushes `{uuid, prompt, data, images}` to the Upstash `input:` prefix
2. Server pops requests and runs each through the v2 LangGraph graph
3. Classifier sets intent + flags; react router re-entrantly runs Scrapy lore search, image processing, or re-description as needed
4. Mechanics fan-out runs 6 pure sub-nodes in parallel; context refresh + summarizer update rolling memory
5. Story is generated, result pushed to the `output:` prefix (persistent state under `games:`)
6. Frontend reads result by UUID from the `output:` prefix

## Edge Cases Handled

Empty queue (poll backoff), Redis failure (graceful None), model errors (try/except per node), memory pressure (3s backoff), concurrent storms (semaphore cap of 16), orphaned requests (TTL cleanup), router/budget overruns (force-to-story terminators), sub-node crash (per-node error patch, merge continues).

Full details in [ARCHITECTURE.md](ARCHITECTURE.md).
