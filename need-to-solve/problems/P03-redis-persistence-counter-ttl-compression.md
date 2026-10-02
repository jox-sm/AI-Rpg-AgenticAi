# P03 — Redis Persistence: Requeue Orphan + Counter Split-Brain + TTL Skew + Compression Write-Only

Status: OPEN. Severity P0.

## Description
1. `redis/input_queue.py:28-29` `requeue()` calls `set_json(request.uuid,...)` -> writes `input:{uuid}` string, never `RPUSH input:queue`. Orphan key, consumer never sees it.
2. Counter split: `redis/game_state.py:62` `hset(uuid,"counter","0")` (hash field) vs `redis/client.py:250-257` `incr/set_counter` on separate string `games:{uuid}:counter` with no `ex`. `try_drain :72` increments string counter before upsert, no rollback on fail -> skews `DRAIN_THRESHOLD=10` (`game_state.py:13`).
3. TTL skew: `client.py:84-90 set_json` always `ex=ttl or 3600`, no persist. `save_initial_state :50,63 + expire :259-262` only expire hash. `hset/incr/hdel` don't refresh TTL -> active game hash can expire mid-session while counter/lock survive. `set_counter SET` without `ex` leaks.
4. Compression write-only: `game_state.py:60-61 compress_text(story)` stores base64-gzip, `load_state :32-42` does plain `json.loads` with no `decompress_text` (`utils/compression.py:13-18` swallows to `None`, 0 callers) -> story never decoded, falls back to raw blob string.
5. Key scheme prefix-only (not DB0/1): `input:queue|delayed|dead`, `output:{uuid}`, `games:{uuid}:state|counter|lock`, transient `input:queue:processing|trigger:busy` (API only). `push_request(uuid,data)` ignores uuid for key (`client.py:173-177`). `KEYS/dbsize` O(N) over REST (`client.py:112-126`), `MEMORY/INFO` unsupported -> `None/{}`.

## Evidence
- `rpg_ai_server/redis/input_queue.py:11-32`, `redis/client.py:57-90,112-159,162-287`, `redis/game_state.py:16-95`, `utils/compression.py:8-18`

## Impact
Lost retries, diverging drain counters, mid-game state expiry, unreadable story field, misleading DB logs (`main.py:24` logs DB numbers ignored by Upstash).

## Repro
Enqueue -> `requeue()` -> `LLEN input:queue` unchanged, `GET input:{uuid}` orphan. Save state, wait 3600s active -> hash gone, counter remains.

## Related
S03, D03, P04, P11.
