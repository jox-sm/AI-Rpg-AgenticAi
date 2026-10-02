# D12 — Tools: Auto-Gen from Registry vs Hand-Curated?

Problem: P12. Solution: S12.

## Options
A. Auto-gen `@tool` from `SKILL_REGISTRY` + CI assert — no drift, but generic descriptions, less prompt control.
B. Hand-curated 8 + explicit exclude list — prompt-tuned, but must maintain (current drift proves it rots).
C. Merge `skills/` into `tool_defs/` (one layer) — fewer files, loses pure `(dict)->dict` testability.

## My take
A + hand-written descriptions in registry (prompt lives with skill, not wrapper). Keeps testability + no drift.

## Question
Are `rarity_enhancer/craft_with_choice/list_workers/check_mastery` intentionally hidden, or accidental? That decides exclude list.
