# S05 — Engine: Blocking Semaphore, Cancelable Stop, Real Backpressure

Best practice:
- Concurrency: `await semaphore.acquire()` before `create_task`, release in `finally` + `done_callback(discard)`. Parse `GameRequest` before acquire. Cap 8-16 for LLM-bound (not 100). `await asyncio.wait(active, FIRST_COMPLETED)` to reap.
- Stop: `for t in active: t.cancel()`; `await wait_for(gather(...,return_exceptions=True), timeout=5)`; `shield()` trailing cleanup; stop mover after tasks.
- Backpressure: check `psutil RSS + queue_len + LLM 429 rate`, not output `%`. Every N completions (not dequeues). On pressure: `await semaphore` block (no new tasks), log + metric, no busy `sleep(3)` on main loop. Fail-closed (shed) if Redis unobservable.
- Separate `request_timeout 120s` via `wait_for` per task, not global hang.
