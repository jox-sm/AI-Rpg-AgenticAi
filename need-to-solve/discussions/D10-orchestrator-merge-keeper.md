# D10 — Merge: Allowlist vs Full Overwrite vs Full Replace?

Problem: P10. Solution: S10.

## Options
A. Allowlist merge (my S10): only stats/inventory/story from persisted — safe, but must maintain list.
B. Full replace with fresh `initial_state` each turn (stateless) — simplest, loses long memory unless RAG covers.
C. Full overwrite with persisted (current) — preserves everything incl. stale budgets — buggy.

## My take
A + coerce dict->model. B would need RAG to be perfect (it isn't yet 0.88 top-1 only).

## Question
What must persist across turns vs recompute? Is `remaining_steps` ever legit to persist, or always fresh 60?
