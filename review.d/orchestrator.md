# orchestrator — engine split (commit pending)

## What moved
`rpg_ai_server/engine/orchestrator.py` (287 lines) → `engine/orchestration/`:
- `state.py` (141): `hydrate_models`, `build_initial_state` (pure state construction)
- `graph_run.py` (71): `run_graph` (lock keeper + timeout/recursion handling)
- `constants.py`: `GRACEFUL_ERROR_STORY`
- `orchestrator.py` remains a 141-line facade holding the `GameOrchestrator` class
  with `__init__`, `initialize`, `process_request` and thin delegates for the moved helpers.

## Dependency findings
- Module-level helpers need one extra relative-import level (`..config` → `...config`) —
  same trap as the worldgen split; caught by import check.
- `process_request` must stay a **class method**: `tests/test_orchestrator.py` does
  `orch._build_initial_state = lambda req: MINIMAL_STATE` (instance-level monkeypatch),
  and `process_request` calls `self._build_initial_state(...)` — preserved.

## Surprises / risks
- First mechanical slice dedented `process_request` to module level → 36 collection/test
  failures (`'GameOrchestrator' object has no attribute 'process_request'`). Fixed by
  re-indenting lines 51–137 by four spaces. Verified 42/42 targeted tests after fix.
- Subagents reported transient test pollution while this file was mid-edit — expect
  clean results only after all parallel agents finish (orchestrator runs the full suite centrally).

## Tests
42/42 targeted (`test_orchestrator`, `test_session_seed`, `test_new_player_scenarios`,
`test_persistent_game`) after fix. Full suite pending central run.
