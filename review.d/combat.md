# combat_system — combat resolution split (in progress)

## What moved
`rpg_ai_server/scripts/combat_system.py` (528 lines at HEAD, ~465 in older notes) →
package `rpg_ai_server/scripts/combat/`, sliced mechanically by line range from the
committed original (no retyping):

| module | lines | content (original line range) |
|---|---|---|
| `common.py` | 35 | `DAMAGE_TYPE_EFFECTIVENESS`, `STATUS_EFFECTS`, `EFFECT_TO_DAMAGE_TYPE` (18–52) |
| `damage.py` | 165 | `resistance_modifier`, `calculate_base_damage`, `apply_damage_multipliers`, `resolve_attack`, `_roll_hit_location` (55–220) |
| `defense.py` | 76 | `resolve_dodge`, `resolve_block`, `resolve_armor` (223–304) |
| `status.py` | 94 | `apply_status_effect`, `_damage_type_to_effect`, `process_status_effects` (307–414) |
| `turn.py` | 110 | `full_combat_turn` (417–528) |
| `__init__.py` | 1 | package docstring |

The original file is now a **25-line facade** re-exporting the same objects: all 15
defined names (functions + dict constants) plus the 9 `dice_engine` names that were
in its namespace (`Dice`, `attack_roll as dice_attack_roll`, `probability_of_success`,
`roll`, `roll_total`, `roll_with_advantage`, `roll_with_disadvantage`, `success`,
`success_with_bonus`). No caller used the unused dice aliases, but keeping them means
*any* `from ...combat_system import X` still resolves exactly as before.

New relative imports go one level deeper (`from .dice_engine` → `from ..dice_engine`).

## Dependency / cycle findings
- Dependency graph is strictly one-way, **no cycles**:
  `turn → {damage, status} → common → (dice_engine)`, `defense → dice_engine`.
  `damage` calls `_roll_hit_location`/`calculate_base_damage`/`apply_damage_multipliers`
  internally; `status` calls `_damage_type_to_effect` and recurses into itself — all
  same-module, so no cross-package edge. No local import was needed (unlike worldgen).
- Existing callers already use local imports and need no edit:
  - `agents/flee.py:167` `from ..scripts import combat_system as _cs` → `_cs.resolve_attack`
  - `agents/mechanics/damage.py:19` `from ...scripts import combat_system as _cs`,
    then `getattr(_cs, "resolve_attack", None)` with an `AttributeError` guard —
    facade re-export satisfies it.
- No test module imports `combat_system` directly; combat is exercised indirectly
  through `node4_parallel`/`flee`.

## Surprises / risks
- Dict constants (`STATUS_EFFECTS`, `DAMAGE_TYPE_EFFECTIVENESS`, `EFFECT_TO_DAMAGE_TYPE`)
  are re-exported as the *same objects*, so in-place monkeypatching (the node4
  `_SUBNODES` lesson) still works. Rebinding `combat_system.STATUS_EFFECTS` on the
  facade would NOT propagate into `status.py` — no current caller does this, but worth
  noting for future tests.
- `process_status_effects` and `apply_status_effect` mutate caller-owned dicts/lists in
  place. Moved unchanged; verified via differential test with deep-copied inputs.
- The file was 528 lines, not the ~465 quoted in the skill/notes — all of it moved.

## Verification
- `python -c "import rpg_ai_server.scripts.combat_system"` → `ok`.
- All 24 expected names present on the facade; `resolve_attack` is the same object.
- AST/inspect comparison: every function body and constant is **byte-identical** to
  `git show HEAD:.../combat_system.py`.
- **Differential test**: loaded the HEAD module into memory and compared 500 seeded
  calls (all 12 functions, 50 seeds each) against the refactored facade — 500/500
  identical outputs.
- Targeted pytest (`test_difficulty`, `test_flee`, `test_xp_loot`,
  `test_classifier_parallel`): first clean run **64 passed / 1 failed**; the single
  failure is `test_xp_loot.py::test_dead_flag_persists_and_game_over_set`
  (`CharacterStats is not subscriptable`), confirmed to fail identically with the
  original HEAD file restored — a known baseline failure, not a regression.
- Re-runs later in the session picked up 5 extra `ModuleNotFoundError: ...engine.config`
  failures and a `flee/__init__` collection error. These come from **concurrent
  subagents** mid-edit (`engine/orchestration/graph_run.py` has `from ..config.settings`
  one level too shallow; `agents/flee/` package being assembled) — unrelated to this
  split and left untouched per the no-outside-files rule. The orchestrator's central
  full-suite run (after those agents settle) is the authoritative check.

## Risks / follow-ups
- Facade kept for at least one refactor cycle; callers have not been migrated.
- If a future test monkeypatches the constants by rebinding on the facade, either patch
  `combat.common`/`combat.status` directly or add a module `__getattr__` shim.
- No git add/commit performed (per rule); orchestrator commits after full suite.
