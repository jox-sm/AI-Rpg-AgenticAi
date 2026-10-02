# P05 — Engine: Unbounded Concurrency + No-Cancel Shutdown + Dead Backpressure

Status: OPEN. Severity P0.

## Description
1. Advisory limit: `engine/multi_tasker.py:116-122` `if len(_active_tasks)>=100: sleep(0.05)` then always `create_task`. Fast producer spawns >>`max_concurrent_requests=100` (`settings.py:59`), piles on `semaphore :72`. `GameRequest(**raw)` inside semaphore, on fail `except ... request.uuid :84` -> `UnboundLocalError`.
2. `stop() :42-49` sets `_running=False` + `gather(return_exceptions)` never cancels. 120s request (`settings.py:69`) blocks shutdown. `run() :124-131 except CancelledError: break` then `await stop()` re-cancelled; `_active_tasks` mutated by callbacks during `gather`. `QueueManager.stop()` before tasks strands delayed items (`queue.py:71-83` mover stops while `handle_failure` still pushes).
3. Backpressure `multi_tasker.py:51-69,98-102` + `redis/output_cache.py:27-36`: counter per dequeue not completion, `sleep(3.0)` blocks main loop head-of-line, single re-check then `return False` ignored ("continuing..." and dequeues anyway). `memory_pressure_ok` fail-open True on exception; `MEMORY/INFO` unsupported on Upstash -> always True. Checked every 100 dequeues, not RSS/LLM 429/queue lag.

## Evidence
- `rpg_ai_server/engine/multi_tasker.py:16-131`, `redis/output_cache.py:27-36`, `redis/client.py:128-159`, `config/settings.py:59-61,69`

## Impact
OOM under burst (100 concurrent `ainvoke` x LLM + state), SIGTERM hangs, memory gate never fires.

## Repro
Burst 200 enqueues -> `_active_tasks` >100. Fill output Redis -> gate still True. `stop()` with hanging `ainvoke` -> blocks 120s.

## Related
S05, D05, P01, P06.
