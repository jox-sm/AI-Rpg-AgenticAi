# D08 — Schemas: Strict at Edge vs Schemaless Debug?

Problem: P08. Solution: S08.

## Options
A. Strict Pydantic at HTTP edge (`response_model`, `UUID4`, `ge/le`) — prevents corruption, but frontend must send clean data, more 422s initially.
B. Schemaless debug API (current) explicitly non-prod, auth-gated — fast iteration, but engine can read garbage.
C. Middle (current implicit): prod API that accepts anything — worst.

## My take
A for `/queue/push|/output|/games/state`, C→B for `/keys|/dbsize` (debug-only).

## Question
Can web app guarantee `UUID4 + valid stats`, or do we need migration period with warnings not 422s?
