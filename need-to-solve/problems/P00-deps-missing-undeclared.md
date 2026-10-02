# P00 — Missing / Undeclared Dependencies [FIXED 2026-09-29]

Status: FIXED. Severity was P0.

## Description
`rpg_ai_server/requirements.txt:1-16` declared langchain/langgraph/redis/upstash/httpx/pydantic/dotenv/Pillow/nltk/pytest but code imported `fastapi`, `uvicorn`, `aiohttp`, `anyio` without declaration. Clean `pip install -r` -> `ModuleNotFoundError: fastapi` at `rpg_ai_server/redis_api.py:13`. `redis_api.py:17-19` guarded `aiohttp` as optional -> silently skipped `NEXTJS_WEBHOOK` POST at `:124-130` with no log. Tests used `@pytest.mark.anyio` (`tests/test_redis_api.py:29+`, `test_lock_client.py:45,62`) relying on transitive `anyio==4.13.0` via httpx, not declared. `Pillow` declared but 0 importers (`import PIL` fails) — bloat.

## Evidence
- `rpg_ai_server/requirements.txt:1-16` (before fix)
- `rpg_ai_server/redis_api.py:13,17-19,24,124`
- `tests/test_redis_api.py:4,7`, `tests/test_lock_client.py:45,62`
- Installed: `fastapi 0.138.0`, `uvicorn 0.49.0`, `aiohttp 3.13.5`, `anyio 4.13.0`

## Impact
API un-runnable on fresh env. Webhook silently dropped. Test suite non-hermetic by accident.

## Repro
`pip install -r rpg_ai_server/requirements.txt --force-reinstall --no-deps` on clean venv -> `python -c "from rpg_ai_server import redis_api"` fails.

## Related
S00, D00. Leaves `redis[hiredis]` unused (only Upstash REST used) — keep or delete, see D00.
