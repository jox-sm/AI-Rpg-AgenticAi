# D07 — Config: Pydantic-Settings vs Dataclass+os.getenv?

Problem: P07. Solution: S07.

## Options
A. `pydantic-settings` fail-fast aggregated error — best DX, one new dep (already installed transitively 2.13.1). Must touch all `os.getenv` sites.
B. Keep dataclass, add manual validators — less churn, but still scattered, no env-file cascade.
C. Minimal: fix `.env` path + `int()` try/except only.

## My take
A. You hit import-time `ValueError` with no context twice already; aggregated error pays off day one.

## Question
OK to add `pydantic-settings` explicitly to requirements and rewrite `settings.py`, or do you want minimal C to unblock live run first?
