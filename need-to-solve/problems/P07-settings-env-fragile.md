# P07 — Settings / Env Fragile + Dead Fields

Status: OPEN. Severity P1 (blocks live).

## Description
`config/settings.py:10-11` loads `rpg_ai_server/.env` (`parents[1]` from `config/`), not repo root — root `.env` silently ignored. Every numeric does bare `int/float(os.getenv)` in `default_factory :16-72` -> malformed `REDIS_PORT=abc` raises at import `:83`, crashes both entrypoints. No validation. `RedisConfig.host/port/input_db/output_db/password :16-20` never read by `client.py:57-66` (only `upstash_rest_url/token`), yet `main.py:24` logs DBs as if matter. `main.py:42` always `GameMemory()` even when `search.configured False :25-28`. `redis_api.py:82 NEXTJS_WEBHOOK=os.getenv` bypasses Settings, no `""` vs None handling. `models.py:9-32` passes `None` API keys into langchain factories -> deep 401, not startup fail. Hardcoded `HTTP-Referer/X-Title :28-29`. Split imports: `main.py:7-16` relative (`python -m`) vs `redis_api.py:9-11` sys.path hack + absolute; `__init__.py` empty.

## Evidence
- `rpg_ai_server/config/settings.py:10-83`, `config/models.py:9-52`, `main.py:20-44`, `redis_api.py:82`, `redis/client.py:57-66`

## Impact
Misconfig surfaces late as 401/empty search, wrong .env path wastes onboarding, dead fields mislead ops.

## Repro
Set root `.env` only -> ignored. Set `REDIS_PORT=abc` -> import crash with no context.

## Related
S07, D07, P00.
