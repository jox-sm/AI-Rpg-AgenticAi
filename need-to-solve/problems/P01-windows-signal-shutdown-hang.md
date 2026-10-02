# P01 — Windows Signal + Shutdown Hang

Status: OPEN. Severity P0.

## Description
`rpg_ai_server/main.py:53-70` builds `shutdown_event`, gets loop via deprecated `asyncio.get_event_loop()` inside async (should be `get_running_loop()`), registers `SIGINT/SIGTERM` via `loop.add_signal_handler`. On Windows ProactorEventLoop this raises `NotImplementedError`, caught at `:63` with only a warning. `shutdown_event` is then never set, so `await shutdown_event.wait()` at `:70` hangs forever. `SIGTERM` has no Windows semantics (need `SIGBREAK`). `Ctrl-C` does not trigger graceful disconnect of 3 Redis clients at `:83-85`.

## Evidence
- `rpg_ai_server/main.py:59,60-64,70,80-81,90`

## Impact
Worker cannot be stopped cleanly on Windows. Must kill process, risks orphaned locks (`games:{uuid}:lock` TTL 30s) and stranded `input:queue:processing`.

## Repro
Run `python -m rpg_ai_server.main` on Windows, press `Ctrl-C` -> hangs, no "Shutting down..." log.

## Related
S01, D01, P05 (engine shutdown), P04 (locks).
