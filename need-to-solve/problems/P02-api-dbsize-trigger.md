# P02 — API Crashes: /dbsize + /trigger Status + Data Loss

Status: OPEN. Severity P0.

## Description
1. `/dbsize` default branch `rpg_ai_server/redis_api.py:378-384`: `for p,client in prefix_map.items(): cl = await client` — `client` is `RedisClient|None`, not awaitable -> `TypeError` always. `if c is None` conflates "no prefix" with "not connected".
2. `/trigger` `redis_api.py:85-139`: `return {"error":...},409` at `:95` serializes as 200 `[dict,409]`, must `raise HTTPException`. Hardcoded `input:queue`, `trigger:busy`, `input:queue:processing` bypass `_key()` prefix helpers. Broad `except: return items:0` at `:100-101` swallows Redis errors. Bare `json.loads(raw_item)` at `:108` -> one poison entry 500s whole drain. `if not state: continue` at `:118-120` drops items then still deletes processing queue + busy at `:136-137` = loss. Stub `{"sid":...,"story":"(processed)"}` uses `sid` vs canonical `GameOutput.uuid`, never calls `GameOrchestrator/MultiTaskEngine`.
3. `/queue/push` `:154-156` uses `Query` for POST body + bare `json.loads(data)`, `uuid` shadows stdlib. `/games/{uuid}/state` `:205-206` checks `if raw is None` but real `hgetall` returns `{}` -> 404 never fires. `game_state_set_field :229` stores raw string while get tries `json.loads` — asymmetric. Per-item `aiohttp.ClientSession()` at `:125-130` risks socket exhaustion.

## Evidence
- `rpg_ai_server/redis_api.py:66-77,85-139,153-159,205-206,216-239,353-357,364-394`

## Impact
Default observability endpoint always 500. Trigger path is placeholder that loses queue items and diverges from worker pipeline.

## Repro
`GET /dbsize` -> 500. `POST /trigger` with one bad JSON in queue -> 500, queue stuck in `input:queue:processing`.

## Related
S02, D02, P03, P06.
