# D14 — Dedup: Delete Scripts vs Promote to Canonical?

Problem: P14. Solution: S14.

## Options
A. Delete dead (`strategy_damage|incident_learning|mastery_formula|swarm_helper`) to `docs/research/`, canonicalize to `skills/base+utils/mastery` — lean, loses prototypes.
B. Promote `combat_system/world_generator` to canonical, rewrite skills as wrappers — preserves sim depth, bigger rewrite.
C. Keep both (current) — guarantees drift (already `1.3/1.7/2.2` vs `0.5/0.75/1.0`).

## My take
A now (ship), B later if combat depth needed. C is indefensible — same `success_check` name, two distributions.

## Question
Is `full_combat_turn` sim depth used by design docs, or is `skills/` arcade math enough? That picks A vs B.
