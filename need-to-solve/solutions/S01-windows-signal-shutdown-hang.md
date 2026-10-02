# S01 — Windows Shutdown: Running Loop + Poll Fallback

Best practice:
- Use `asyncio.get_running_loop()` inside async, never `get_event_loop()`.
- Try `add_signal_handler(SIGINT,SIGBREAK)`; on `NotImplementedError` fall back to `threading.Event` + `signal.signal()` + periodic `shutdown_event` poll (0.2s) in `engine.run()`.
- `stop()`: cancel `_active_tasks`, `await gather(*tasks, return_exceptions=True)` with 5s timeout via `wait_for`, then disconnect clients in `finally`.
- Exit via `return`, not `sys.exit(1)` inside async; let `asyncio.run` propagate code.
Test: run on Windows, `Ctrl-C` / `Ctrl-Break` -> "Shutting down..." within 1s, locks released.
