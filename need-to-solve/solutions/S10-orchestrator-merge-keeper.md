# S10 — Orchestrator: Allowlist Merge + Abort on Lock Loss

Best practice:
- Merge allowlist: only `character_stats/skills/inventory/relationships/story/counter` from persisted, never `remaining_steps/needs_*/prompt/images`. Coerce: `if isinstance(stats,dict): CharacterStats(**stats)` before graph + before N7.
- Lock keeper: `while True: sleep(ttl/3); if not refresh: cancel graph task + raise LockLost` (abort, not continue). Use single `worker_id` from engine.
- `images: List[ImageData]` handling with `isinstance` guard for dict vs model.
- Return `Result(ok, output|None, reason)`; `compiled_graph is None` fails at `initialize()`, not per-request.
