# P14 — Skills/Tools/Scripts Triplication + Dead Code + Import-Time Heaviness

Status: OPEN. Severity P2 (debt → P1 drift).

## Description
3 dice/success/damage paths: `scripts/dice_engine.py:55-65 skill_check d20>=DC` vs `skills/base.py:21-54 success_check` (mastery? `mastery_check random<rate :58` else `randint+level+bonus>=DC`) vs `scripts/combat_system.py:68-86,113-205` + `skills/combat_offense:9-35` + `combat_tools:9`. `dice_tools:136` reuses `scripts/dice_engine`, skills ignore both. `scripts/mastery_formula:6-19` fork of `utils/mastery.py:45-55` dead (extra `level_boost`), only `utils/` wired (`crafting:70`, `base:31`, `worker_manager:146`). `mastery.py:49,54 sf==0 ZeroDivision`, `:46-48,65-67 None` fallback to `smithing` can be None -> TypeError, `:77 diff 0` ZeroDivision. `openrouter_client:13-21` no key check (`Bearer None`), fixed timeout, no retry, `extract_json :69-71` unchecked. `items_db.py:11-20,72-102` NLTK download at import, hardcoded `items-db` path (`mastery:14`, `worker_manager:15` same), non-list JSON skipped, empty DB no error. Duplicate fuzzy `_char_bigrams` pad `" "` vs `"#"` (`items_db:23-32` vs `knowledge:216-224`, thresholds `0.05/0.65`). `swarm_helper:84-99 new_event_loop` crashes async, 0 callers, `skipped` never set, ordering lost, `format :115-144` misclassifies. `worker_manager:24-25,39-50,76-95,143` 0 callers, substring `in` false positives, dynamic `mastery_{skill}_level` keys, lazy import cargo-cult. `scripts/combat:449-453 def_statuses=[]` always empty, `:154-159` double dodge, `strategy_damage:306-307` 20x chain, `:534-564` drops resist + double kills, `:359,366,377` jitter floor bias. `incident_learning:271-287` double counts. `world_generator:11,35-36,75,135-137` eager DB, hex-seed RNG, int difficulty crash. `knowledge:11,68-83,227-325` eager DB, 80-line BoW ignores helpers. `skills/crafting:5` unused imports, `:14` duplicates `mastery_tools:298` map, `magic:157` typo comment.

## Evidence
- `rpg_ai_server/skills/*.py`, `utils/*.py`, `scripts/*.py`, `agents/node4_tool_agent/tool_defs/*.py`

## Impact
Formula drift already visible, triple memory (`ItemsDB()` x3), offline import breaks, 1000+ dead lines hide bugs.

## Repro
`grep -r "def success_check\|def mastery_rate\|def calculate_base_damage"` -> 3+ hits divergent. `python -c "from rpg_ai_server.skills.knowledge import X"` triggers NLTK download.

## Related
S14, D14, P12.
