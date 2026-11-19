---
name: clean-architecture
description: Project architecture + compaction rules for the RPG AI server (Python/FastAPI/LangGraph). Apply when refactoring, adding features, or "compacting"/shortening this codebase. Enforces layered dependencies, OOP, DRY, and small files with behavior-preserving moves.
---

# Clean Architecture — RPG AI Server

Use this skill for **every** code change in `rpg_ai_server/` and `tests/`. Goal: a codebase an agent can enter cold — small files, one reason to change per file, dependencies pointing one way, zero duplicated logic.

## 1. The dependency rule (non-negotiable)

```
config/          settings, model slugs, timeouts. Env only. Imports NOTHING above.
   ↑
schemas/         pure data contracts (pydantic/dataclasses). No I/O.
   ↑
utils/           stateless helpers + the single LLM client + items DB adapter.
   ↑
redis/           infrastructure adapters (queue, state, output, search memory).
   ↑
agents/          graph nodes. Business logic. NO FastAPI, NO direct httpx, NO raw Redis.
   ↑
engine/          composition: graph_v2, orchestrator, bootstrap, multi_tasker.
   ↑
api.py, redis_api.py   thin HTTP controllers: auth/validate → delegate to engine.
```

- Imports point **downward only**. An agent never imports from `engine/` or API modules. API never implements game logic inline.
- Cross-cutting concerns (logging, coercion, JSON parsing, LLM calls, key prefixes) live in `utils/` or `config/` — exactly one implementation.

## 2. DRY — the single-source list

Check these before writing any helper; if it already exists, **import it**:

| Need | Use (only) |
|---|---|
| LLM call (text or JSON) | `utils/openrouter_client.py` → `chat_completion` / `chat_json` |
| Tolerant JSON extraction | `utils/openrouter_client.py` → `_parse_json_content` |
| dict-or-model coercion | `utils/coerce.py` → `as_dict`, `stat_of`, `to_int` |
| Redis access | `redis/client.py` clients + Lua ops; never raw REST in a node |
| Game state merge | `redis/state_manager.py` allowlist merge |
| Redis key prefixes / TTL | `config/settings.py` constants — never literal `"games:"`, `"output:"`, `"input:"` in nodes |
| Items lookup | `utils/items_db.py` — never read `items-db/` directly |
| Config values | `config/settings.py` (`settings.*`) — never `os.getenv()` outside config |
| Structured logs | `utils/logger.py` |

**Red flags:** `httpx.post(...)` in an agent, `json.loads` with custom fence stripping, `os.getenv` in a node, a second state merge, copied prompt boilerplate, magic numbers replacing settings.

## 3. OOP / function design

- Classes own state + behavior together; prefer **composition over inheritance**. No god-objects, no static utility classes (use module functions).
- One public function = one job; typical signature ≤ 5 params (bundle into a pydantic contract otherwise).
- Pure functions for transformations (nodes take state, return state patches). Side effects only in `redis/` adapters.
- Exceptions carry context; `try/except` never swallows silently — log with `utils/logger.py`.
- Type hints on every public function. Dataclasses/pydantic over loose dicts crossing module boundaries.

## 4. Compaction budgets

| Unit | Soft limit | Hard limit |
|---|---|---|
| File | 200 lines | 250 (split it) |
| Function | 30 lines | 40 |
| Class | 100 lines | 150 |
| Module public exports | 5 | — |

When splitting a large file:
1. **Move code unchanged** into focused modules.
2. Leave a compatibility facade: the original module re-exports the moved names (one-line `from .x import ...`), so imports and tests stay valid.
3. Run targeted tests, then the full suite. **Never mix a move with a behavior change** — that is a separate commit/step.
4. Keep facade files for at least one refactor cycle; delete only after all callers migrate.

Known hotspots (split targets, in priority order):
`agents/node4_parallel.py` (673) → `mechanics/{dice,damage,stats,skill,inventory,json}.py` + `fanout.py` facade;
`engine/world_generator.py` (636) → `world/{grid,entities,lifecycle}.py` + facade;
`agents/combat_system.py` (465), `utils/xp_loot.py` (342), `agents/flee.py` (275), `redis/client.py` (288), `engine/orchestrator.py` (287).

## 5. Refactor procedure (safety)

1. **Baseline**: `pytest -q` — observed 2026-11-19: **224 passed / 8 failed** (1 each in `test_orchestrator_hard`, `test_turn_system`, `test_xp_loot` + 5 memory tests still asserting pre-503 behavior). Record exact failures before touching code.
2. One module per step; no behavior change; compatibility re-exports.
3. Run the module's tests, then the full suite; compare to baseline. Any NEW failure → revert that step.
4. Review `git diff --stat` — each step should be small and explainable.
5. Live API contract stays stable (`REDIS_API.md` is authoritative): endpoint paths, key prefixes, `GameRequest` shape, `output:{sid}` + `timestamp`, and the web relay contract never change silently.

## 6. Definition of done

- [ ] Dependencies point downward; no upward/cyclic imports
- [ ] Every cross-cutting concern has exactly one owner
- [ ] Files/functions within budgets (or a documented exception)
- [ ] Public API unchanged (facades in place)
- [ ] Test results match baseline; no new failures
- [ ] Comments/docstrings explain *why*, not *what*
