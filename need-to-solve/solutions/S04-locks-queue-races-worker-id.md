# S04 — Locks + Queues: Lua Atomicity, UUID Worker-IDs, Live Heartbeat

Best practice:
- `pop_delayed_due`: Lua `ZRANGEBYSCORE + ZREMRANGEBYSCORE` atomically or `BZPOPMIN` on native Redis. Single mover guard (`asyncio.Lock` + `if _mover_task: return`).
- `release/refresh_lock`: Lua `if redis.call("GET",KEYS[1])==ARGV[1] then return redis.call("DEL",KEYS[1]) else return 0 end`. Same for refresh with `EXPIRE`.
- `worker_id = f"worker-{uuid4().hex[:8]}"` at startup, stable for process lifetime, passed to both `QueueManager` and `Orchestrator` (one ID, not two `id()`).
- Heartbeat: `asyncio.create_task(heartbeat_loop 5s)` in `MultiTaskEngine.start()`, `stop()` cancels it last. Or delete heartbeat + `input:workers:*` if unused.
- Contention: return `MISS` sentinel, engine sleeps 0.1s without `retry_count++` (see S06).
