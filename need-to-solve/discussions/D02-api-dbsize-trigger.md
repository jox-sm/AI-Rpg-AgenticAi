# D02 — API: Delete /trigger vs Fix to Delegate vs Keep Debug-Only?

Problem: P02. Solution: S02.

## Options
A. Delete `/trigger` — one path (`main.py` worker). Simplest, no drift. Loses serverless trigger.
B. Fix to delegate to `Orchestrator` (my S02) — keeps Vercel `trigger:busy+RENAME` model, but must maintain two runners.
C. Mark `/trigger|/keys|/dbsize` debug-only, auth-gated, never prod.

## My take
A if you run worker 24/7; B only if Next.js must wake serverless. Current stub is worst of both — deletes data without doing work.

## Question
Do you need serverless wake, or is worker always-on? If always-on, can I delete `/trigger`?
