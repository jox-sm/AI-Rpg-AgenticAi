# D09 — Graph: Keep LangGraph vs Plain Chain?

Problem: P09. Solution: S09.

## Options
A. Keep LangGraph + checkpointer + `N5_refresh` — pays off if you add human-in-loop/time-travel, but keeps interpreter + double-budget complexity.
B. Plain `async def pipeline` with `for _ in range(4)` — 60 lines vs 146, no dunder, single budget, faster. Loses graph viz/checkpoint.
C. Keep as-is (linear + 4 detour with stale context) — least churn, keeps staleness bug.

## My take
B unless you can name a checkpoint feature you will use in next month. Current graph buys little over chain.

## Question
Do you plan agentic loops deeper than 4, HITL, or time-travel? If no, can I collapse to chain?
