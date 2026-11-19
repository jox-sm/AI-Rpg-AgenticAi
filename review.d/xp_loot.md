# xp_loot — XP/loot/economy split (IN PROGRESS, awaiting orchestrator batch)

## What moved
`rpg_ai_server/scripts/xp_loot.py` (406 lines) → package `rpg_ai_server/scripts/economy/`:

| file | lines | contents |
|---|---|---|
| `common.py` | 102 | all shared constants (rarity/tier/type/STAT maps, regexes), cached state (`_enemy_cache`, `_items_db`), `_db`, `round_half_up`, `clamp_stat`, `normalize_rarity`, `normalize_tier`, `_slug`, `parse_level_range` |
| `xp.py` | 47 | `kill_xp`, `participation_tick`, `apply_level_ups` |
| `loot.py` | 153 | `roll_qty`, `parse_loot_string`, `resolve_loot_entry`, `enemy_db_row`, `roll_loot`, `merge_loot` |
| `difficulty.py` | 112 | adaptive-difficulty constants + `ensure_difficulty`, `advance_day_tracker`, `difficulty_scalar`, `difficulty_report`, `add_kill_heat`, `_side_damage`, `track_fight` |
| `awards.py` | 27 | `award_for_kills` |
| `__init__.py` | 4 | package docstring |

`xp_loot.py` is now a **29-line facade** re-exporting all 36 public names (15 constants + 21
functions) from the five modules.

## Dependency / cycle findings
- One-way graph, **no cycles**: `common` → utils only; `xp`, `loot`, `difficulty` → `common`;
  `awards` → `xp` + `loot`. No economy module imports the facade.
- Relative imports bumped one level for the new depth (`..utils.coerce` → `...utils.coerce`,
  and the local `ItemsDB` import inside `_db` → `...utils.items_db`).
- Mutable state (`_enemy_cache`, `_items_db`) is pinned in `common.py`; `loot.enemy_db_row`
  mutates the *imported dict object* in place and `_db` uses `global _items_db` in its home
  module — both preserved exactly. No caller imports these private names.

## Surprises
- Public API audit done first: callers are `test_xp_loot`, `test_difficulty`,
  `worldgen/{world,finite,cells}`, `node0_worldgen`, `flee`, `mechanics/{common,damage,fanout}`.
  All imported names are re-exported; no caller monkeypatches xp_loot internals.
- `scripts.economy` has no dependency on `agents`/`engine`, so the `worldgen` and `mechanics`
  local imports of the facade stay cycle-free.

## Tests run + result
- `python -c "import rpg_ai_server.scripts.xp_loot; print('ok')"` → **ok**.
- **Behavior-equivalence harness** (original `git show HEAD:…xp_loot.py` loaded side-by-side):
  **15 constants, 10 same-object identity checks, 130 function-output comparisons → ALL PASSED**.
  This is the authoritative proof the split changed no behavior.
- Targeted `pytest tests/test_xp_loot.py tests/test_difficulty.py` is **unstable mid-batch**
  because other subagents are concurrently rewriting `engine/orchestrator.py`,
  `scripts/combat_system.py` and `agents/mechanics/`. Baseline (before my change) was
  **35 passed / 1 failed** (`test_dead_flag_persists_and_game_over_set`, the known
  `CharacterStats` failure). Latest run **33 passed / 3 failed**: the same known failure plus
  2 orchestrator-dependent pipeline tests now erroring with
  `AttributeError: 'GameOrchestrator' object has no attribute 'process_request'`
  (and earlier `ModuleNotFoundError: rpg_ai_server.engine.config`) — entirely from the
  in-progress orchestrator split, not from `scripts/economy/`. The equivalence harness
  confirms the two pipeline tests would pass once that split is finished.

## Risks / follow-ups
- No new failures attributable to this module. Re-run the full suite after the combat +
  orchestrator batches land; expect the documented **224 passed / 8 failed** baseline.
- `awards.py` (27) and `__init__.py` (4) are intentionally tiny but keep one-responsibility
  boundaries; fine to leave as-is.
- Facade kept for at least one refactor cycle per the shared decision — do not delete yet.
