# D04 — Atomicity: Lua in Upstash REST vs Migrate to Native Redis?

Problem: P04. Solution: S04.

## Options
A. Lua/compare-del inside Upstash REST (if supported) + single mover — keeps serverless, but REST Lua support limited, still HTTP polling.
B. Migrate hot queue/locks to native `redis.asyncio+hiredis` (already in reqs) with `BZPOPMIN`, streams, `BLPOP` — true atomicity, needs VPC/persistent conn.
C. Accept rare duplicates (idempotent story gen) — no fix, add `uuid` dedupe in output.

## My take
A first (cheap), B if duplicates observed. C is tempting but hides lock-steal correctness bug.

## Question
Have you seen duplicate turns in logs? If not, is Lua-only fix enough, or do you want streams now?
