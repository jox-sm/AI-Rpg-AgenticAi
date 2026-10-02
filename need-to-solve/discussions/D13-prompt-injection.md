# D13 — Injection: Strict Tags vs Filter vs Nothing?

Problem: P13. Solution: S13.

## Options
A. Strict delimit + role separation (my S13) — robust, +10% tokens, needs prompt rewrites + guard test.
B. Blocklist (`"error"`, `"ignore previous"`) — cheap, bypassable, drops legit prose (current bug).
C. Nothing (current) — fastest, poisoned lore -> story, stored jailbreak persists.

## My take
A. You already inject web + RAG into player-facing story — highest exploit surface. Blocklist is worse than nothing (false security).

## Question
Accept token overhead for tags on every turn, or only for web/RAG sections to save tokens?
