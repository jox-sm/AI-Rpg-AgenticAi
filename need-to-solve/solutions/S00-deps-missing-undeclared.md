# S00 — Dependencies: Declare Truth (DONE)

Best practice: `requirements.txt` must equal imports. Scan with `pip freeze` + `grep ^import/^from`.

Applied:
```
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30,<1.0
aiohttp>=3.9,<4.0
anyio>=4.0,<5.0
```
Removed `Pillow` (0 importers). Kept `redis[hiredis]` with comment "future local only".
Verify: `pip install -r`, `pip check` clean, `python -c "from rpg_ai_server import redis_api"`, `pytest -q`.
Rule: add pre-commit `pip-missing-reqs` or `deptry` to block undeclared imports.
