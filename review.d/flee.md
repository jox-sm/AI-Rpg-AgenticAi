# flee — flee subsystem split (in progress, no commit by this agent)

## What moved
`rpg_ai_server/agents/flee.py` (312 lines in the working tree) → package
`rpg_ai_server/agents/flee/`. The old `flee.py` was **deleted** — a package and a
module of the same name cannot coexist (Python picks the package, verified
empirically), so the package `__init__.py` is the compatibility facade.

- `__init__.py` (21 lines) — facade; re-exports all original public names as the
  *same* function objects, including the module-level `random` symbol that tests
  reach through `flee_mod.random`.
- `common.py` (71) — constants (`MAX_ENGAGED`, `FLEE_TIMEOUT_SECONDS`,
  `TRICK_ITEM_KW`, `BLIND_KW`, `JEV_SYSTEM`) + `_roll_d100`, `live_hostiles`,
  `engage_pack`, `currently_engaged`, `skill_level`, `has_trick_item`,
  `flee_chance`.
- `tricks.py` (59) — `_fallback_trick`, `adjudicate_trick`.
- `retaliation.py` (20) — `monster_strike`.
- `resolve.py` (134) — `resolve_flee` (kept intact; see risks).

Code was moved by line-range slicing; only import headers changed. Every
relative import was deepened by one level (`..scripts` → `...scripts`,
`..config` → `...config`, `..utils` → `...utils`). No `.flee` self-imports
remained because all callees now live inside the package.

## Dependency / cycle findings
- One-way: `resolve → {common, retaliation, tricks}`, `tricks → common`,
  `retaliation → common`. No module-level cycles.
- **Monkeypatch coupling was the real constraint.** `tests/test_flee.py` patches
  `flee_mod._roll_d100`, `flee_mod.random`, and the string path
  `rpg_ai_server.agents.flee.adjudicate_trick`. With a plain split, `resolve_flee`
  would look those names up in `resolve.py`'s globals and the patches on the
  facade would be ignored. Fixed by a **local import inside `resolve_flee`**:
  `from . import _roll_d100, adjudicate_trick`. At call time the package is fully
  initialized, so this is exactly the facade attribute (patched or not).
  `random` needs no such trick: it is the stdlib module singleton, so mutating
  `flee.random.randint` reaches `common._roll_d100` too.
- Verified explicitly with a standalone script that the string-path patch of
  `adjudicate_trick` is honored by `resolve_flee` (result `skill=acrobatics`,
  `blind=True`, `bonus=0.3`), and that all re-exported names are identical
  objects (`is` checks) to the submodule definitions.

## Surprises
- The task brief said "~275 lines"; the working-tree file was actually 312.
- The facade cannot live in `flee.py` once a `flee/` package exists (package
  wins on import). This differs from the node4/worldgen splits, where facade and
  package had different names. Hence `__init__.py` is the facade and the target
  file was removed.
- `GameOrchestrator.process_request` was temporarily dedented out of its class
  by a *concurrent* orchestrator subagent, making the 3 pipeline flee tests fail
  on their first action (`AttributeError` before any flee code runs). I did not
  touch that file; the agent fixed it, after which all 23 tests passed again.
  Recorded here so the orchestrator does not misread a transient red run.

## Tests
- Import check: `from rpg_ai_server.agents.flee import resolve_flee, engage_pack,
  monster_strike` → `ok`.
- `python -m pytest tests/test_flee.py -q` → **23 passed** (baseline was 23).
- Broader targeted run (`test_flee.py test_classifier_parallel.py
  test_difficulty.py`) → **47 passed**.
- Full suite intentionally NOT run by this agent (orchestrator runs it centrally).

## Risks / follow-ups
- `resolve_flee` remains a ~130-line function (pre-existing hard-limit
  violation). Splitting its internals would be a behavior change, so it was left
  intact. Defer to a dedicated, separately-tested step.
- `adjudicate_trick` is 43 lines and `_damage_patch` in `damage.py` calls into
  the facade — both are pre-existing exceptions, untouched.
- The facade re-exports the flee-defined names plus `random`; the incidentally
  imported coerce helpers (`as_dict`, `to_int`, …) and `re`/typing names are no
  longer attributes of `rpg_ai_server.agents.flee`. No caller or test uses them
  (grep confirmed), but a downstream `from ...flee import to_int` would break.
  Add re-exports there if such a caller ever appears.
- Keep the facade for at least one refactor cycle; `damage.py` still imports
  `resolve_flee`, `engage_pack`, `monster_strike` from `..flee`.
