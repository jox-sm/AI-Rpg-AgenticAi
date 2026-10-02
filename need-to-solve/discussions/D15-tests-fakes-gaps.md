# D15 — Tests: Hermetic Fakes vs Staging Integration?

Problem: P15. Solution: S15.

## Options
A. Keep hermetic fakes + contract tests (fast CI) — 8s, but `RENAME`/ranking/semantics unmodeled.
B. Add staging Upstash job (slow, needs secrets) — catches `hgetall {}`, `bytes`, prefix bugs, but flakes + cost.
C. Both (my S15): fakes for unit, staging nightly for drain/query/trigger — best, most maintenance.

## My take
C. 82 green currently proves little for P0 paths. At minimum contract tests (no infra) to catch sig drift.

## Question
Can I get staging Upstash creds + nightly run, or must CI stay offline-only? If offline-only, accept that `/trigger` stays untested?
