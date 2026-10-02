# D00 — Deps: Pin Strict vs Range vs Delete Unused?

Problem: P00. Solution: S00.

## Options
A. Range pins (`>=,<`) — flexible, done. Risk: future breaking minor.
B. Strict `==` freeze — reproducible, but Dependabot noise.
C. Delete `redis[hiredis]` too (truly unused) vs keep for local dev.

## My take
A + keep `redis` with comment. You already have `pip check` clean; strict freeze only for Docker release.

## Question for you
Keep `redis[hiredis]` for future local, or delete to keep truth? If delete, local dev must use Upstash only — OK?
