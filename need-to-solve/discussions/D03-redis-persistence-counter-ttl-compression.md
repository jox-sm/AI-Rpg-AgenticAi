# D03 — Redis: One DB + Prefixes vs 3 DBs vs Flat Hash?

Problem: P03. Solution: S03.

## Options
A. Keep 1 Upstash + prefixes (`input:/output:/games:`) + fix TTL/counter/codec — zero infra change, but `KEYS` O(N), TTL skew must be manually maintained.
B. Flat per-game hash `game:{uuid}` holding queue+state+counter+lock fields — fewer keys, single TTL, but loses clean client split.
C. 3 real Upstash DBs — independent quota/eviction, triple config/connections.

## My take
A. You have no isolation need to justify C; B is bigger migration. Fix `touch()` + single counter now.

## Question
Any quota/noisy-neighbor pain today to justify C, or is prefix confusion (DB0/1 docs) the only cost?
