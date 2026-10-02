# Progress — D&D RPG AI System (current)

AI server `D:\AI agent` (Python FastAPI + LangGraph v2). Web-app contract lives in `REDIS_API.md`.

## What the system IS now
- Graph v2 (`engine/graph_v2.py`): classifier → react_router ⇄ {search|image|redescribe} (≤3 passes) → mechanics (N4 parallel fan-out) → context_refresh → summarizer → story → pusher; budget/deadline force-exit to story, keeper cancels graph on lock loss.
- Models: OpenRouter-only (`config/models.py`); Node1 web search via Scrapy (no Google key).
- Redis: Lua atomic ops (`redis/client.py` — locks, delayed-pop, touch, counter); `QueueManager` uuid worker + single-mover guard; `GameStateManager` allowlist merge, drain threshold 25.
- Memory: Upstash Search `game-memory` index (server-side embeddings), sid-scoped; node4 read path injects `rag_context`.
- Tests: 113 pass (`pytest -q`), incl. contract tests.

## Verified LIVE 2026-10-03
- Full turn end-to-end: 40.8s, real story pushed, no error.
- Live classifier: attack/goblin report @ 0.98.
- Upstash Lua locks / delayed-pop / touch / state / drain: all pass on real REST.
- Model slugs re-probed live; defaults updated to verified working slugs.

## What's left
- `/trigger` RENAME → Lua atomic drain.
- Strict Pydantic edge schemas (D08).
- Search creds unconfigured (drain fail-closed, expected).
- Free-tier 429 flakiness on some model slugs.

## Boot
- Engine worker: `python -m rpg_ai_server.main` (from `D:\AI agent`)
- API: `python -m uvicorn rpg_ai_server.redis_api:app --port 8055`
- Tests: `pytest -q`
