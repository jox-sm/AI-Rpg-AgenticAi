# worldgen — world generator split (DONE, commit 5515aae)

## What moved
`rpg_ai_server/scripts/world_generator.py` (636 lines) → package `rpg_ai_server/scripts/worldgen/`:
`common.py` (constants, biome map, seeded RNG, item-db lists, `coord_to_key`),
`finite.py` (6x6 generation + GridCell projections), `patches.py` (sparse overlay),
`cells.py` (deterministic per-coordinate cells), `world.py` (ensure/read/expand),
`movement.py` (parse + move). Original file is now a 27-line facade.

## Dependency findings
- `patches.patch_cell` reads `get_world_cell` from `world.py`, while `world.py` reads
  `get_patches`/`coord_to_key` from `patches.py` — a real module-level cycle.
- Fixed with a **local import inside `patch_cell`** (no behavior change), the same
  pattern already used elsewhere in this codebase for deferred imports.

## Surprises / risks
- First generated version failed collection: moving from `scripts/` to
  `scripts/worldgen/` requires `..schemas` → `...schemas` in headers too — caught
  immediately by the import check, fixed before tests.
- No tests monkeypatch world_generator internals; facade re-exports cover every caller
  (checked: `node0_worldgen`, `orchestrator`, `flee`, and 4 test modules).

## Tests
63/63 targeted (`test_worldgen_expand`, `test_new_player_scenarios`,
`test_persistent_game`, `test_difficulty`); full suite baseline preserved exactly.
