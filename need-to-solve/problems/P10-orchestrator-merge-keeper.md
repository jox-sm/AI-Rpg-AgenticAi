# P10 — Orchestrator Merge Overwrite + Lock Keeper Split-Brain

Status: OPEN. Severity P1.

## Description
1. `engine/orchestrator.py:125-131`: on existing state `for k,v in existing.items(): if k in initial: initial[k]=v` overwrites fresh request fields with stale persisted values — incl. `remaining_steps` (exhausted -> immediate forced route), `needs_search/image/re_description` (spurious reroute), `character_stats` stored dict vs init `CharacterStats` object `:43 vs :150` -> `node7:19 model_dump()` crash.
2. `_keep_lock_alive :179-184`: sleeps `refresh 10s` vs `ttl 30s` (`settings.py:71-72`) OK, but on `refresh False` just returns while `ainvoke :188-194 timeout 120s` keeps running unlocked -> two workers same uuid.
3. `img.get("url") :103-105` assumes dict, crashes if `GameRequest.images` Pydantic. Function-local imports `:97-99`. `initialize()` never tested, `output None :160` conflated with lock-miss. `engine/__init__.py` empty.

## Evidence
- `rpg_ai_server/engine/orchestrator.py:28-31,42-138,141-206`, `agents/node7_output_pusher.py:19-22`

## Impact
Replayed budgets, wrong reroutes, concurrent duplicate stories, type crashes.

## Repro
Save state with `remaining_steps=11`, new prompt same uuid -> immediate force to node4. Kill lock mid-run -> second worker starts, both push output.

## Related
S10, D10, P04, P08, P09.
