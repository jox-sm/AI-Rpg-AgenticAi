# S06 — Failure Taxonomy: Success vs Retry vs DLQ vs Miss

Best practice enum:
- `OK(output)` -> ack, no retry.
- `HARD_FAIL(validation, GraphRecursion, Timeout)` -> `handle_failure` with backoff, after 3 -> DLQ `input:queue:dead` with `error, traceback[:2000]`.
- `LOCK_MISS` -> requeue head without `retry_count++`, `sleep 0.1`, metric `lock_contended`.
- `POISON(json error)` -> immediate DLQ, log `queue_pos`, continue drain (never abort whole `/trigger`).
- Orchestrator returns `Result` dataclass, never `None`-overload or graceful-story-as-success. Graceful story only for player-facing fallback + still counts as `HARD_FAIL` for DLQ.
- Codec: `try json.loads` per item, `except -> DLQ`, never bare.
