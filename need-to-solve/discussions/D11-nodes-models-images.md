# D11 — Models: Free-Tier + Retry vs Paid Mini vs Self-Host?

Problem: P11. Solution: S11.

## Options
A. Free + retry + fallback (my S11) — $0, but 429s, truncation, `json_object` ignored. Needs pagination + repair code.
B. Paid mini (`qwen-coder-mini`, `gemini-flash-lite`) for N2/N3/N6 — reliable JSON, costs cents/1K turns, less code.
C. Self-host VLM for grids — deterministic, heavy ops.

## My take
A now to ship, B for N2/N3 first when you can spend. 225 cells in 8K will never be reliable on free.

## Question
Budget per 1K turns? If $0 strict, accept paginated 3-call grids (3x latency)? If small budget, which nodes get paid first?
