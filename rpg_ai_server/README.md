# D&D RPG AI Server

An async D&D RPG AI server built with **LangGraph**, **LangChain**, and **Google Gemini SDK**. Processes game requests via Redis through a 7-node LangGraph pipeline and returns generated narratives.

## Quick Start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # add your API keys
python -m rpg_ai_server.main
```

## Architecture (7-Node Pipeline)

```
Redis DB 0 (input) → MultiTaskEngine → LangGraph Pipeline → Redis DB 1 (output)
```

| Node | Role | Model | Type |
|------|------|-------|------|
| **Node 1** | Web search (lore/rules) | Gemini 2.0 Flash | Conditional |
| **Node 2** | Image → 15×15 grid analysis | Nemotron Nano (OpenRouter) | Conditional |
| **Node 3** | Re-describe grid (time change) | OWL-alpha (OpenRouter) | Conditional |
| **Node 4** | Tool agent: dice, damage, stats, skills, inventory, JSON tracker | Qwen Coder (OpenRouter) | Reactive |
| **Node 5** | Context summarization | Nemotron Super (OpenRouter) | Main |
| **Node 6** | Story generation | Qwen Coder (OpenRouter) | Main |
| **Node 7** | Push result → Redis DB 1 | — | Final |

**Flow:** `START → Node5 → Router → [Node1/2/3 loop] → Node4 → Node6 → Node7 → END`

## Project Structure

```
rpg_ai_server/
├── config/          Environment & model config
├── schemas/         Pydantic models, enums, LangGraph state
├── redis/           Input queue + output cache (2 Redis DBs)
├── agents/          One module per node (Node1–Node7)
├── engine/          Graph builder, orchestrator, multi-tasker
├── utils/           Logger, OpenRouter HTTP client
└── main.py          Entry point
```

## Key Features

- **Async multi-tasking** — up to 100 concurrent requests via `asyncio.Semaphore`
- **Memory backpressure** — checks Redis output DB memory every 100 requests; waits 3s if >90%
- **6 D&D mechanics tools** — dice roller, damage multiplier, stats/skills/inventory/JSON tracker
- **All models free-tier** — uses OpenRouter free models + Gemini free tier
- **1-hour TTL** — requests/results auto-expire from both Redis databases

## Configuration

Set in `.env`: `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`, Redis host/port, model names, concurrency limits, memory thresholds.

## How it Works

1. Frontend pushes `{uuid, prompt, data, images}` to Redis DB 0
2. Server pops requests and runs each through the LangGraph pipeline
3. Router decides if web search, image processing, or re-description is needed
4. Tool agent handles all game mechanics (dice, combat, stats, inventory)
5. Context is summarized, story is generated, result pushed to Redis DB 1
6. Frontend reads result by UUID from Redis DB 1

## Edge Cases Handled

Empty queue (poll backoff), Redis failure (graceful None), model errors (try/except per node), memory pressure (3s backoff), concurrent storms (semaphore cap), orphaned requests (TTL cleanup), infinite loops (recursion limits).

Full details in [ARCHITECTURE.md](ARCHITECTURE.md).
