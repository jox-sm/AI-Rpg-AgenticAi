# D06 — Failures: Strict DLQ vs Lenient Continue?

Problem: P06. Solution: S06.

## Options
A. Strict taxonomy (my S06): poison->DLQ, hard-fail->retry3->DLQ, lock-miss->no-penalty. Correct, but more code + DLQ triage needed.
B. Lenient: graceful story always, never DLQ — player never sees error, but bugs hide, poison loops forever.
C. Current inverted: graph fail as success, lock-miss as fail — worst.

## My take
A. You already have DLQ tables (`input:queue:dead`) unused for main fails — wire them.

## Question
Who triages DLQ? If no one, does strict just fill a table no one reads — should `/queue/dead` alert to Discord/webhook?
