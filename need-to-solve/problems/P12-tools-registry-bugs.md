# P12 — Tool Registry Drift + Logic Bugs

Status: OPEN. Severity P1.

## Description
`agent.py:19-29` imports 9 incl. `rarity_enhancer`, `:162-171` registers 8 — `rarity_enhancer` never exposed. `tools.py:11-24`, `tool_defs/__init__:11-24` export `craft_with_choice/list_available_workers/check_mastery` never registered. Prompt `:32-49` documents 7, omits `rarity/use_skill` split.
Bugs: `inventory_tools:93 json.loads(dict)` TypeError (should `else item_json`). `stat_tools:12-18,54-57 should_level_up` unread, every XP full heal + `current_load=0`, `stat_cap` twice contradictory. `dice_tools:136 SCDice` unused, `count 1-100` docstring `:115` never validated before `sc_roll :143-146` (`0/-5` -> `total=modifier` valid). `combat_tools:61 _value2member_map_` private API, unknown type coerces to BLUDGEONING, no try around `DamageCalculation`. `data_tools:38-39` outside try, list payload -> TypeError. `skill_tools:64,68 float` to `int` field, `stat_bonus level//4+strength//4` ignores dex/int/wis. `mastery_tools:79 unused key`, `:194 w in at_location` dict equality O(n²) fragile. `agents/__init__:1` empty, deep relative imports fragile.

## Evidence
- `rpg_ai_server/agents/node4_tool_agent/agent.py:19-217`, `tools.py:11-24`, `tool_defs/*.py`, `skills/__init__.py:1-24`

## Impact
LLM can't use advertised rarity/craft/worker tools, XP heals exploit, dice/combat silent wrong results.

## Repro
List registered tools vs prompt vs `SKILL_REGISTRY` -> mismatches. `inventory_checker({"item_json": {...dict...}})` -> TypeError.

## Related
S12, D12, P13, P14.
