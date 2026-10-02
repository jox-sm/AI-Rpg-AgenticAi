# S03 — Redis Persistence: One Counter, Refresh TTL, Roundtrip Codec

Best practice:
- Delete `InputQueue.requeue`; all retries via `QueueManager.handle_failure` -> `RPUSH` or delayed zset.
- Single counter: `games:{uuid}:counter` string with `EX 3600`, remove hash-field counter. `incr` + `expire` atomically (Lua or pipeline). Roll back on drain fail (or increment after success).
- TTL: helper `touch(uuid)` -> `expire(state)+expire(counter)` on every `hset/incr/hdel`. `set_json(..., persist=False)` param; `push_result` uses default TTL, game state uses refresh.
- Compression: either drop (store plain JSON, Upstash handles) OR symmetric: `save: compress->hset`, `load: try decompress else json.loads else raw`. Add roundtrip test. Fix `decompress` to never return None silently (raise + DLQ).
- Keys: central `Keys` class, no hardcoded strings. `KEYS` only for debug, never in hot path; `dbsize` via `pipeline dbsize` or counter.
