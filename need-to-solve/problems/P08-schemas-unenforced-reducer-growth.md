# P08 — Schemas Unenforced + Reducer Growth

Status: OPEN. Severity P1.

## Description
`schemas/types.py:38-133`: `GameRequest.uuid: str` not UUID4, `timestamp 0.0` no `ge=0`, `images List[Dict]` untyped. `DiceRoll advantage+disadvantage` both True allowed, `results/total` unchecked. `DamageCalculation.total` free. `CharacterStats health/max_health/mana/max_mana` no `ge/le` or `health<=max`, `skills Dict[SkillType,int]` negative allowed, `resistances Dict[DamageType,float]` unbounded. `InventoryItem quantity ge=0` allows 0-qty, `durability vs max` unchecked. `ContextSummary recent_events max_length=20` + `narrative max 500` raise not truncate.
`schemas/state.py:20-46 GameState(TypedDict,total=True)` requires all 20 keys though many `Optional`. `skills/inventory/relationships :30-32` + `tool_results :42` are `Annotated[List,operator.add]` reducers that append every loop pass -> unbounded growth unless overwritten. `__next__: str :46` required but router may leave unset. Neither entrypoint validates: `main.py` never imports schemas, `redis_api.py` defines ad-hoc `Memory*Request :283-296` (`top_k` no bounds, `documents list[dict]` unvalidated) and passes raw `Query` strings.

## Evidence
- `rpg_ai_server/schemas/types.py:18-150`, `schemas/state.py:20-46`, `schemas/enums.py:4-109`, `redis_api.py:283-296,353-357`, `engine/orchestrator.py:42-111`

## Impact
Invalid stats/dice pass to LLM tools, 500s on narrative length, state lists bloat across loops/retries, HTTP can corrupt hashes engine reads.

## Repro
`CharacterStats(health=9999,max_health=10)` passes. Loop 4 passes -> `tool_results` length 4x.

## Related
S08, D08, P09, P10.
