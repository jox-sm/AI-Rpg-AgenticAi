# S15 — Tests: One Async Runner, Contract + Staging

Best practice:
- Standardize: `anyio` + `anyio_backend="asyncio"` fixture in `conftest.py` (keep `@mark.anyio`), drop `_run()` helpers. Add `pytest.ini: asyncio_mode` NOT mixed. Declare `anyio` (done).
- Contract tests: `assert set(Fake.method sig)==set(Real.method sig)`, `hgetall {} vs None`, `push_dead timestamp source`, `bytes vs str` lock.
- Fix fakes to match real: prefix/suffix keys, `expire>0`, `connect/disconnect`, `keys/delete/dbsize`, semantic stub with scores.
- Add missing: `/trigger` drain+poison, `/delayed|dead`, `/counter|lock|expire`, `/keys|dbsize`, `memory_pressure`, `multi_tasker` cancel, real `GameStateManager`+fakes roundtrip. Remove privates coupling, `MINIMAL_STATE` copy per test.
- Staging job: Upstash dev DB for `drain/query/export` + `RENAME` atomicity (fakes can't model).
- Fix `_graphify_run.py`: `dotenv_values`, guard `BACKENDS.get`, no `argv` mutate, no `""` key.
