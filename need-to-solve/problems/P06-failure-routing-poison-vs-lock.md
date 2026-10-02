# P06 — Failure Routing Inverted: Graph Fails as Success, Lock-Miss as Failure, Poison Dropped

Status: OPEN. Severity P0.

## Description
1. `engine/orchestrator.py:162-172` catches all incl. `GraphRecursionError :195-197` + `TimeoutError :198-200` into `{"story": GRACEFUL_ERROR_STORY}`. `multi_tasker.py:77` treats non-None as success -> retry/DLQ (`queue.py:47-66`) dead for graph fails.
2. `orchestrator.py:119-122` returns None on lock contention, `:160` returns None on no output — conflated. `multi_tasker.py:78-80` treats None as failure -> `handle_failure` increments `retry_count`, `backoff 5*2^retry :14-15`, `MAX_RETRIES=3 :10` -> contended live requests dead-letter, hot-loop via delayed zset.
3. `redis/input_queue.py:15-23` swallows pop/validation to None indistinguishable from empty -> `multi_tasker.py:110-112 sleep(0.1)` loops, poison silently dropped never DLQ. `queue.py:37-45 next_request` no try — same payload raises in one path, vanishes in other.
4. Serialization asymmetry: `client.py:92-98,166-171,196`, `redis_api.py:109,156` bare `json.loads` -> 500/abort; `game_state.py:48 dumps(default=str)` coerces then `load_state :32-42` returns raw string — type drift.

## Evidence
- `rpg_ai_server/engine/orchestrator.py:113-205`, `engine/multi_tasker.py:71-88,104-112`, `redis/queue.py:10-66`, `redis/input_queue.py:11-32`

## Impact
Real failures never retried, healthy contended requests killed, poison either crashes trigger or vanishes.

## Repro
Force `GraphRecursionError` -> output graceful story, no DLQ. Two workers same uuid -> retry_count burns to dead.

## Related
S06, D06, P04, P05.
