# redis/client — Redis client family split (commit pending)

## What moved
`rpg_ai_server/redis/client.py` (346 lines) → `redis/clients/`:
- `tls.py` (47): legacy-TLS httpx subclasses + the import-time `_patch_httpx_legacy_tls()` call
- `base.py` (125): `RedisClient` (prefixing, JSON, Lua, admin helpers)
- `input_client.py` (80): `InputRedisClient` (queue, delayed/dead, heartbeat)
- `output_client.py` (16): `OutputRedisClient`
- `games_client.py` (105): `GamesRedisClient` (state hash, counters, locks, TTL)
- `client.py` remains a 21-line facade re-exporting all 9 original names.

## Dependency findings / critical invariant
- Original line 47 calls `_patch_httpx_legacy_tls()` at **module import time**, before
  `from upstash_redis import AsyncRedis`. `base.py` imports `.tls` before importing
  upstash, and the facade imports `.clients.base` first — verified at runtime:
  `httpx.Client.__name__ == "_LegacyTLSClient"` after importing the facade.
- Relative imports in the sliced TLS header needed `..config` → `...config` (same
  one-level-depth trap as prior splits).

## Risks / follow-ups
- Facade kept for one refactor cycle; callers (`bootstrap`, `redis_api`, `game_state`,
  `output_cache`, `queue`, tests) import unchanged.
- No behavior changes; mechanical line-range slicing.

## Tests
Import check passed; full suite result recorded in review.md merge notes.
