# D01 — Shutdown: Graceful-Cancel vs Kill-Fast vs Poll Loop?

Problem: P01. Solution: S01.

## Options
A. Poll + cancel (my S01) — 1s responsive, clean locks. Cost: extra thread/poll code.
B. Kill-fast: `os._exit(1)` on Ctrl-C — simple, but orphan locks 30s, corrupts `processing` queue.
C. Move to Linux/Docker only — sidesteps Win Proactor, but you dev on Win.

## My take
A. Locks are correctness, not nicety. 30s orphan x concurrent turns = duplicate stories.

## Question
Accept 50 lines of Win-specific shutdown code, or mandate WSL/Docker for engine and keep POSIX signals only?
