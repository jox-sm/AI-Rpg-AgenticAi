# S14 — Dedup: One Formula, Lazy DB, Delete Dead

Best practice:
- Canonical: `skills/base.success_check + damage_formula` + `utils/mastery` ONLY. Delete `scripts/mastery_formula`, `combat_system` fork OR promote `combat_system` and make skills thin wrappers — never both. Add `sf<=0` guard, `diff!=0` guard, validate `min<=max`.
- `ItemsDB`: single `get_items_db()` lazy singleton in `utils/items_db.py`, no NLTK at import (`try stopwords else fallback set()` offline-safe), `Path` via env `ITEMS_DB_DIR`, one bigram impl.
- Delete 0-caller: `swarm_helper`, `worker_manager` (or wire heartbeat), `strategy_damage`, `incident_learning` (or move to `docs/research/`). `world_generator` lazy DB, handle `int|str|None` difficulty.
- No eager `ItemsDB()` at module top; function-level `get_db()`.
