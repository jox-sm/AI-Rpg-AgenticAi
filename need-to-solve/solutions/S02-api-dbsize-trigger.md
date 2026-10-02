# S02 — API: Lifespan + HTTPExceptions + Thin Façade

Best practice:
- Replace `@app.on_event` with `lifespan` + `app.state` clients, single shared Upstash client, `await close()` on exit.
- `raise HTTPException(409,"not triggered")`, never `return dict,code`.
- `/trigger`: delete stub OR delegate: `rename` with Lua guard, `LPOP` loop with per-item `try/except json` -> DLQ, call `orchestrator.process_request` (not stub), single `aiohttp.ClientSession`, delete `processing` + `busy` in `finally`.
- Use Pydantic `Body` models for POST, not `Query` strings; `uuid: UUID4`. Validate `top_k ge=1 le=20`.
- `/dbsize`: `c = await _get_input()` etc, separate `prefix==""` (aggregate) from `client is None` (503).
- `/games state`: treat `{}` as 404, symmetric `json.dumps/loads` with schema (`CharacterStats` etc).
Test: `GET /dbsize`, `POST /trigger` with poison entry -> 207 partial + DLQ, no loss.
