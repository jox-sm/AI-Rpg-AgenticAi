# S11 — Nodes: Inside-Try, Factory Tokens, Paginated Grid, Retry

Best practice:
- Move `state["uuid"]`, client getters inside `try`; return `{"...":..., "error": None|str}` consistently.
- All LLM calls via `config/models.py` factories (single token budget source). Validate `choices[0].message.content` non-empty, else retry once with fallback model (`:free` -> paid mini).
- JSON: strip ```json fences, `json-repair` fallback, Pydantic-validate cells (`Terrain` enum try, unknown -> `UNKNOWN` + warn, not whole-image fail).
- Grid pagination: 15x15=225 cells -> 3x75-cell calls (5 rows each) then merge; or 7x7 summary + detail on demand. Budget 20K tokens, not 8K. Empty-grid fallback actually called. No in-place `image_data.grid=` mutation; return full `grid_data` map per-image isolated.
- `node1` returns `{"results": [...]|[], "unavailable": bool}` not poison string. Cap free-model `max_tokens` to provider limits.
