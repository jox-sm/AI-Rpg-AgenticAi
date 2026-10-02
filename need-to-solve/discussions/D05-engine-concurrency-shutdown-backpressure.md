# D05 — Concurrency: Low Semaphore (8-16) vs 100 vs Adaptive?

Problem: P05. Solution: S05.

## Options
A. 8-16 blocking semaphore (my take) — matches LLM-bound, prevents OOM/429. Slower burst drain.
B. Keep 100 — fast drain, but OOM + OpenRouter quota burn, gate never fires.
C. Adaptive AIMD on latency/429 — optimal, but 100+ lines + metrics.

## My take
A now, C later. 100 concurrent `ainvoke x 120s` x full state will OOM container before Redis 90%.

## Question
What is your container RAM + OpenRouter RPM limit? That sets the number — 8 or 16?
