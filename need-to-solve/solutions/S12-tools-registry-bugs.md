# S12 — Tools: Single Registry, Fix Logic, Doc = Code

Best practice:
- One source: `SKILL_REGISTRY` -> auto-generate `@tool` wrappers (no hand-duplicated list). CI asserts `set(registered)==set(REGISTRY)-set(EXCLUDED)` + prompt mentions all.
- Fixes: `inventory: else item_json`, `stats: remove auto-heal, single cap formula`, `dice: validate 1<=count<=100`, `combat: DamageType(value) try/except, no private API`, `data: parse inside try`, `skill: int(level)`, `mastery: precompute key, exact id match not dict equality`.
- Keep `skills/(dict)->dict` pure, `tool_defs` handles JSON/LLM only.
