# P04 — Non-Atomic Queue + Lock Races, Worker-ID Collisions, Dead Heartbeat

Status: OPEN. Severity P0.

## Description
1. `redis/client.py:189-196 pop_delayed_due`: `ZRANGEBYSCORE` then `ZREMRANGEBYSCORE` non-atomically. Two `_mover_loop`s (`redis/queue.py:24-35` no duplicate guard) can read same due items -> double `push_request` -> duplicate processing.
2. `client.py:271-287 release_lock/refresh_lock`: `GET` then `DEL/EXPIRE` check-then-act. Stale owner after expiry deletes new owner's lock. Only `acquire_lock SET nx+ex :264-269` is correct.
3. `queue.py:21 _worker_id=f"worker-{id(self)}"`, `orchestrator.py:28-31 f"orch-{id(self)}"` — `id()` process-local, reused after GC, collides across restarts. Unsafe for lock ownership.
4. `client.py:204-207 set_heartbeat(ttl 15)` never called in steady loop (`MultiTaskEngine` never calls `QueueManager.heartbeat :68-69`) -> `input:workers:*:heartbeat` stale.
5. Lock contention path `multi_tasker.py:77-80` treats miss as `handle_failure` -> burns retry budget, hot-loops via delayed zset instead of skip (see P06).

## Evidence
- `rpg_ai_server/redis/client.py:189-196,204-211,264-287`, `redis/queue.py:18-83`, `engine/multi_tasker.py:77-80`, `engine/orchestrator.py:28-31,179-184`

## Impact
Duplicate turns, cross-worker lock steals, phantom worker list, live requests dead-lettered on contention.

## Repro
Two movers + due items -> same uuid processed twice. Expire lock, new worker acquires, old `release_lock` deletes it.

## Related
S04, D04, P03, P06, P10.
