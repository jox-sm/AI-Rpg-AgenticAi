# Progress — D&D RPG AI System (current)

AI server `D:\AI agent` (Python FastAPI + LangGraph v2). Web-app contract lives in `REDIS_API.md`.

## What the system IS now
- Graph v2 (`engine/graph_v2.py`): classifier → react_router ⇄
  {search|image|redescribe} (≤3 passes) → mechanics (N4 parallel fan-out) →
  context_refresh → summarizer → story → pusher; budget/deadline force-exit to
  story, keeper cancels graph on lock loss.
- Models: all LLM calls go through one OpenAI-compatible direct HTTP client
  (`utils/openrouter_client.py`); provider switchable via `OPENROUTER_BASE_URL` —
  **currently NVIDIA NIM** (`https://integrate.api.nvidia.com/v1`):
  - story/redescription/context: kimi-k3.1-pro (superseded by speed-first swap, see below)
  - classifier/jev: minimax-m3.1-flash
  - image: nemotron-3-nano-omni
  - `REQUEST_TIMEOUT_SECONDS=110`; Node1 web search via Scrapy (no Google key).
- Redis: Lua atomic ops (`redis/client.py` — locks, delayed-pop, touch, counter); `QueueManager` uuid worker + single-mover guard; `GameStateManager` allowlist merge, drain threshold 25.
- Memory: Upstash Search `game-memory` index (server-side embeddings), sid-scoped; node4 read path injects `rag_context`. **Currently unconfigured live** → `/memory/*` answer 503 with guidance (gameplay unaffected).
- Tests: 227 pass / 5 pre-existing failures (`pytest -q`) — the 5 memory tests assert 200 while `/memory/*` returns 503 until `UPSTASH_SEARCH_*` is configured; incl. contract tests.

## Verified LIVE 2026-11-18 (NVIDIA NIM)
- OpenRouter → NVIDIA swap done with **zero code changes** (env only: base URL, key, 6 model slugs, `REQUEST_TIMEOUT_SECONDS=110`).
- Live suite: **20 passed / 0 failed / 4 skipped** (memory = Search creds still unconfigured).
- Real E2E turn: 1,436 chars of kimi-pro story in ~74s (fits 110s deadline + web's 120s poll budget).
- `z-ai/glm-5.3-flash` excluded — hangs >120s on every call (probed 3×).

## Model benchmark + speed-first swap (2026-11-18/19)
- Benchmarked 20 NVIDIA NIM models (tiny-call latency + tokens/sec from `usage.completion_tokens`):
  - fastest: `nemotron-3.5-lightning-30b-a3b` 146.9 tok/s (~8.8k measured TPM), 1.6s tiny
  - `bolt-e4b` 50.9 tok/s / 1.1s tiny; `laguna-xs-2.1` 60.9 tok/s; `super-vl-120b` 83.5 (vision)
  - dead/hang: glm-5.3-flash (201s timeout), gpt-oss-20b, step-5-preview
  - 404 on this account: gemma-3-12b/4b-it, cosmos-reason2-8b, starcoder2-15b
- **Live assignment (user directive):** classifier + jev = `bolt-e4b`; JSON context writer =
  `laguna-xs-2.1`; story + redescription = `lightning-30b`; image unchanged (nano-omni).
- Turn latency: 74s → 39s (kimi thinking-off) → **24s** (speed-first); live suite 20/24,
  zero engine errors; story 2,009 chars.

## Verified LIVE 2026-11-16
- Full API surface on the combined service (:8000, real Upstash): **20 passed / 0 failed /
  4 skipped** — health, trigger probe, keys/dbsize (lazy), queue length + push validation
  (bad JSON → 422), state field put/get/delete, whole-state 404, counter, output 404,
  lock acquire/release, and one real engine turn pushed through the queue → output
  written with `timestamp` (story content = OpenRouter 429 message; free-tier quota,
  chain healthy).
- Delete-route semantics documented: `DELETE /keys/{key}?prefix=games` expects the key WITHOUT the client namespace (`{sid}:state`, not `games:{sid}:state`).
- Docker: AI Dockerfile + requirements.txt + compose (web+AI) written; images built and stack verified — see `Dockerfile`, `docker-compose.yml`.

## Verified LIVE 2026-10-03
- Full turn end-to-end: 40.8s, real story pushed, no error.
- Live classifier: attack/goblin report @ 0.98.
- Upstash Lua locks / delayed-pop / touch / state / drain: all pass on real REST.
- Model slugs re-probed live; defaults updated to verified working slugs.

## What's left
- ~~`/trigger` RENAME → Lua atomic drain~~ — retired; `/trigger` is an advisory probe (engine owns the queue).
- Strict Pydantic edge schemas (D08).
- ~~Search creds unconfigured (drain fail-closed, expected)~~ — now surfaces as 503 + actionable detail on `/memory/*`; still needs the Upstash Search pair to enable memory/saves end-to-end.
- Free-tier 429 flakiness on some model slugs (daily quota on `gemma-4-31b-it:free` etc.).

## Boot
- Combined (API + engine, one process): `python -m uvicorn rpg_ai_server.api:app --port 8000`
- Or split: `python -m rpg_ai_server.main` (engine) + `python -m uvicorn rpg_ai_server.redis_api:app --port 8000` (API)
- Or Docker: `docker build -t rpg-ai-server . && docker run --env-file rpg_ai_server/.env -p 8000:8000 rpg-ai-server` — full web+AI stack via `docker-compose.yml` (web on :3000).
- Standard API port is 8000 — the web's `AI_SERVER_URL` default and relays expect it.
- Tests: `pytest -q`
