# node4 — mechanics fan-out split (DONE, commit 640cec9)

## What moved
`rpg_ai_server/agents/node4_parallel.py` (673 lines) → package `rpg_ai_server/agents/mechanics/`:
`common.py` (snapshot, spawn tables, target/strikes/merge helpers), `dice.py`,
`damage.py`, `stats.py`, `skill.py`, `inventory.py`, `json_patch.py`, `fanout.py`
(order, `_SUBNODES`, `node4_parallel`). Original file is now a 30-line facade.

## Dependency findings
- `damage.py` depends on `common` (target/speed helpers) + `inventory` (weapon dice) — one-way, no cycles.
- Relative imports deepened by one level (`..scripts` → `...scripts`, `.flee` → `..flee`).

## Surprises / risks
- `tests/test_classifier_parallel.py` does `monkeypatch.setitem(n4._SUBNODES, "dice", boom)`.
  The facade re-exports the *same dict object*, so in-place mutation still reaches the
  fan-out function — verified by the test. A copy would have silently broken it.

## Tests
47/47 targeted (`test_classifier_parallel`, `test_flee`, `test_difficulty`); full suite
exactly matched baseline 224 passed / 8 failed (same eight known failures).
