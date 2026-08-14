# Gaps — Known Bad Things (Index)

Every known issue, risk, and leftover, dumped in one place. Each gap links to where it's tracked/fixed. This is the "known bad" index — if something is wrong, it lives here first.

---

## A. Immediate bugs / risks in the code

| # | Gap | Where | Fix tracked in |
|---|-----|-------|----------------|
| A1 | **Lock TTL (30s) can expire mid-turn** — LLM turns routinely exceed 30s; `refresh_lock()` exists (`redis/client.py:277`) but is **never called** → two workers can process the same uuid concurrently → state corruption | `redis/client.py`, `engine/orchestrator.py` | 🔴 not yet planned — needs lock renewal loop or per-phase lock re-acquire |
| A2 | **`redis_api.py` has zero auth** — open `/keys`, `/dbsize`, `/keys/{key}`, `/games/*` endpoints; anyone with the URL can read/wipe game state | `redis_api.py` | 🔴 not yet planned — needs shared-secret header / token gate |
| A3 | **No explicit `recursion_limit`** on `ainvoke` — relies on framework default (25 or 1000); runaway loop = raw `GraphRecursionError`, no graceful story | `engine/orchestrator.py:129` | `plan/loops.md` L4 |
| A4 | **node4 ReAct loop unbounded** — no `ToolCallLimitMiddleware`, no duplicate-call guard; a model that keeps calling tools burns tokens to the limit | `agents/node4_tool_agent/agent.py` | `plan/loops.md` L5, L6 |
| A5 | **Router cycle uncapped** — bounded today only because node1/2/3 happen to clear their flags; cross-triggering (node A sets node B's flag) becomes an infinite loop with no defense | `engine/graph_builder.py:94–108` | `plan/loops.md` L1, L2 |
| A6 | **No wall-clock timeout** on `process_request` — a slow loop blocks the worker slot indefinitely | `engine/orchestrator.py` | `plan/loops.md` L7 |
| A7 | **node6 has no output assertions** — empty/garbage story output flows to the player as if valid | `agents/node6_story_generator.py` | `plan/loops.md` L8 |
| A8 | **Error text leaks to the player** — `"The adventure encountered an error: {e}"` exposes internal details | `engine/orchestrator.py:154` | 🔴 not yet planned — generic message + `error` field for logs |
| A9 | **No tracing** — no LangSmith / node-level spans; loop bugs are invisible in a flat log | repo-wide | `plan/loops.md` L9, §7 |

---

## B. RAG / DB-2 leftovers (dead code)

| # | Gap | Where | Fix tracked in |
|---|-----|-------|----------------|
| B1 | `RagCache` wrapper still exists | `redis/rag_cache.py` | `plan/finishing.md` "Remove RAG/DB 2 leftovers" |
| B2 | `RagRedisClient` still constructed | `main.py:29`, `redis_api.py:20,26` | same |
| B3 | `rag_db=2` / `upstash_rag_url` / `upstash_rag_token` settings | `config/settings.py`, `.env.example` | same |
| B4 | rag endpoints still exposed in `redis_api.py` | `redis_api.py` | same |
| B5 | old RAG deps in `requirements.txt` (chromadb etc.) | `requirements.txt` | same |

---

## C. Redis / state gaps (from the integration audit)

| # | Gap | Where | Fix tracked in |
|---|-----|-------|----------------|
| C1 | No field-level dirty tracking — HSETs everything each turn | `redis/game_state.py` | `plan/redisIntegration.md` H9 / `plan/finishing.md` |
| C2 | No `version` field on state Hash (optimistic locking) | schema | M4 |
| C3 | No `status` field (`idle`/`processing`/`error`) — can't detect double-processing | schema | M5 |
| C4 | DLQ never cleaned — `games:queue:dead` grows forever; no alert when > 100 | `redis/queue.py` | `plan/finishing.md` "DB 0" |
| C5 | `games:{uuid}:response` Hash + PUBLISH notify not implemented (web server still relies on fallback polling) | server | H4 (low priority) |
| C6 | Stale-state cleanup Lua script (SCAN + TTL + DEL + vector namespace delete) not implemented | server | C7 / `plan/finishing.md` |
| C7 | Retry counter lives on state (24h TTL) — a >24h processing span resets it → infinite retry loop | `redis/queue.py` | M1 (fix: counter on queue item) |
| C8 | `context_summary` is **never persisted** — `save_state()` only writes `game_data`/`story`/`character_stats`; drain uses only story | `engine/orchestrator.py:134–140` | 🔴 not yet planned |
| C9 | Drain content-hash check (skip if story unchanged) not implemented | `game_state.try_drain()` | H3 |

---

## D. Memory / vector gaps

| # | Gap | Where | Fix tracked in |
|---|-----|-------|----------------|
| D1 | `GET /memory/export/{sid}`, `POST /memory/restore` not implemented | server | `plan/finishing.md` Scenario Lifecycle |
| D4 | Namespace cleanup (game_over + stale sweep) not implemented | server | `plan/redisIntegration.md` G8 |
| D5 | **Embedding-model mismatch risk** — write/query model must be identical; a config change silently degrades recall | config | `plan/ragGameMemory.md` (documented, unguarded) |
| D6 | **Vector free tier: 10k queries/day ≈ 1 per turn** — one active user per turn is fine; a handful of players blows the quota (queries are the tighter limit, not storage) | Upstash plan | documented in `plan/ragGameMemory.md` — no mitigation |
| D7 | **Upstash Redis free tier: 10k cmds/day** — drain bursts (HSET/HGETALL/INCR per turn + sweep) burn it fast | Upstash plan | documented, no mitigation |
| D8 | Export JSON is a single response — very long sessions (> ~4MB) exceed it; needs cursor pagination | `REDIS_API.md` | documented, not implemented |
| D9 | **100-namespace shared index, registry is per-device** — orphaned namespaces from other devices/users; registry cap is client-side only | architecture | `plan/finishing.md` (capped at 20, no server reconciliation) |

> Fullstack/frontend items (Next.js routes, scenario registry, exit popup, autosave, SSE reconnect) are **not tracked here** — the frontend has its own folder.

---

## F. Testing gaps

| # | Gap | Fix tracked in |
|---|-----|----------------|
| F1 | No unit tests: compression roundtrip, `QueueManager` (backoff/delayed/dead), `GameStateManager` (load/save/drain) | `plan/finishing.md` Testing |
| F2 | No integration tests: mock Upstash Redis, vector upsert→query, export→restore roundtrip | same |
| F3 | No loop-guard tests: router flip-flop, futile-action guard, recursion-limit fallback | `plan/loops.md` L10 |
| F4 | No load test against free-tier limits (10k cmds/day Redis, 10k queries/day Vector) | 🔴 not planned |

---

## G. Accepted risks (known, deliberately tolerated)

| # | Risk | Why accepted |
|---|------|--------------|
| G1 | At-most-once queue delivery (RPUSH/LPOP) — a prompt can be lost on worker crash | documented in `REDIS_API.md`; retry lives at client + DLQ |
| G2 | node4 self-grades "done" (model says all mechanics processed) | bounded per-turn, low stakes; external graders exist (incident learning, player) — `plan/loops.md` §6 |
| G3 | `MemorySaver` checkpointer recreated per request | intentional — fresh context per iteration (`plan/loops.md` §5); regression if promoted to cross-turn |
| G4 | Trigger is best-effort (`trigger:busy` 30s) — a trigger POST can be missed, action still queued | `REDIS_API.md` |
| G5 | Namespace wipe on "Don't save" is optional/undoable — memory may persist longer than the player expects | scenario model (`REDIS_API.md`) |

---

## Cross-reference (how gaps map to fix sources)

- **`plan/loops.md`** L1–L10 → A3, A4, A5, A6, A7, A9
- **`plan/redisIntegration.md`** audit (C/H/G/M/U/V/P items) → C1–C7, C9, D4
- **`plan/finishing.md`** checklists → B1–B5, C4–C6, D1, D4, F1–F3
- **`REDIS_API.md`** → D1, D8
- **🔴 not yet planned** (new, need decisions): A1 (lock renewal), A2 (API auth), A8 (error text), C8 (context_summary persistence), F4 (load test)
