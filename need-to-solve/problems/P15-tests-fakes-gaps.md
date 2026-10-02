# P15 — Tests: Fakes Diverge, No Config, Gaps Hide P0

Status: OPEN. Severity P1 (false confidence).

## Description
No `pytest.ini/pyproject/setup.cfg` at root. `conftest.py:1-6` only path, no `anyio_backend`. Mixed `asyncio.run` helper (`test_queue:11-12`, `game_state:8-9`, `orchestrator:10-11`, `loops:7-8`, `search_memory:8-9`) vs `@mark.anyio` (`lock_client:45,62`, `redis_api:29-146`) — works by accident (anyio transitive). Flaky sleeps (`orchestrator:192-228`, `queue:79 approx 10±0.2`). Fakes diverge: `FakeGamesClient :109-165` no prefix/suffix/connect/TTL, `expire True` vs `>0`, `hgetall None` vs `{}` masks `game_state:32-35` bug; `FakeInput :168-206 push_dead time.time` vs `timestamp`, `sort_keys` vs plain, missing `heartbeat/keys/delete/dbsize/connect/client`; `FakeOutput :209-224` missing `set_json/delete/keys/memory_percent`; `FakeSearchIndex :37-106` keyword-overlap + insertion tiebreak ignores rerank/semantic, filter only `@metadata.sid`, `fetch/delete prefix` assume — `search_memory:54-62` holds only on fake. `_SdkBehavior :12-42` single-slot ignores key/ex, hides `bytes vs str` at `client:274-275`. Mocks couple privates (`mem._index.data`, `mgr._memory`, `MINIMAL_STATE` shared mutable `:72-105`, `BoomIndex.data` class attr, `make_router_node(None)` hides None-deref, patch globals `:16-26` never exercises `on_event` deprecated `:66,73` -> 4 warnings). Gaps: `/trigger`, `/delayed|dead`, `/counter|lock|expire`, `/keys|dbsize`, `input_queue|output_cache|multi_tasker|node*|world_generator|openrouter|_patch_tls|clear/restore` untested. `_graphify_run.py:7,9-22,31` hardcoded `.env`, naive parse, `BACKENDS["openai"]` no guard, `""` key, mutates argv.

## Evidence
- `tests/*.py`, `rpg_ai_server/redis_api.py:66-77,85-394`, `redis/*.py`, `engine/*.py`, `_graphify_run.py:7-31`

## Impact
82 green ≠ prod green. P0 `/trigger/dbsize/memory_pressure/multi_tasker` can break with no test red.

## Repro
`pytest -q` 82 passed + 4 `on_event` warnings. Diff fake vs real sig -> mismatches listed.

## Related
S15, D15, P02-P06.
