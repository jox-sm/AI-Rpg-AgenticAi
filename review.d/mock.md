# mock — mock OpenRouter chat script split

## What moved
`rpg_ai_server/scripts/mock_openrouter_chat.py` was **525 lines** (not the ~459 in the
queue) → new package `rpg_ai_server/scripts/mock_chat/` (all code moved verbatim by
line-range slicing):

- `__init__.py` (18) — the `sys.path` bootstrap the original ran before importing
  `tests.fakes` (ROOT now `parents[3]`, one level deeper).
- `common.py` (47) — `STATE_DIR`, `DEFAULT_SID`, `_MONSTERS`, `_seconds`, `_envelope`,
  `_when_true`, `MimicOptions`.
- `client.py` (203) — `MimicOpenRouterClient` (whole 184-line class kept intact) +
  `install_mimic`.
- `session.py` (128) — `MockState`, `MockSession` (fake Redis/Upstash + real graph).
- `cli.py` (136) — `_print_story`, `_run`, `_repl`, `main` + the `__main__` guard.

Original file is now a 22-line compatibility facade re-exporting the **same objects**
(verified by identity checks: `m.MimicOpenRouterClient is client.MimicOpenRouterClient`,
etc.); all 16 `__all__` names resolve.

## Dependency / cycle findings
- One-way chain: `common ← client ← session ← cli`. No cycles, no local-import hacks needed.
- The original's project imports were all **absolute** (`rpg_ai_server....`), so the
  "bump relative imports by one level" rule did not apply to them — only the
  `parents[2] → parents[3]` path bootstrap changed.
- `install_mimic`'s existing local import of `rpg_ai_server.utils.openrouter_client`
  was preserved exactly.
- Bootstrapping in `__init__.py` guarantees `tests.fakes` is importable before
  `session.py` is first imported, regardless of which submodule a caller touches.

## Surprises
- `main()` feeds `__doc__` to argparse, so moving it to `cli.py` would have silently
  changed `--help`. `cli.py`'s first docstring line is kept verbatim; `--help` output
  is byte-identical.
- `from __future__ import annotations` initially masked a missing `List` (session)
  and `dataclasses` (session) import — the code uses `dataclasses.field`. Caught by a
  `typing.get_type_hints` sweep and by the first smoke run; both fixed.
- Two **temporary failures came from parallel agents' in-progress edits, not this
  split**: `engine/orchestration/graph_run.py` briefly had `..config.settings`
  (should be `...config.settings`), and `orchestrator.process_request` was momentarily
  outside `GameOrchestrator`. Both were fixed by those agents; end-to-end then passed.
- No Python module or test imports this file (grep only hits docs). It is launched as
  `python -m rpg_ai_server.scripts.mock_openrouter_chat`. Its docstring's
  `rpg_ai_server.utils.mock_chat` path is stale — left unchanged (doc text only).

## Tests run + result
- Import check: `python -c "import rpg_ai_server.scripts.mock_openrouter_chat; print('ok')"`
  → `ok`.
- Deterministic harness over all pure/mostly-pure logic (`_classify`, `_jev_trick`,
  `_context`, `_images`, `_story`, `chat_completion`, `_envelope`, options) run before
  and after: 276-line JSON output **identical** (only timestamped log lines differ).
- `--help` description identical; `--say "slay the goblin"` full graph run → exit 0
  with story / mechanics / state sections intact.
- Facade identity + `__all__` checks pass. No targeted pytest uses this mock (grep),
  so none was run. Full suite intentionally not run here (orchestrator runs it
  centrally); baseline **224 passed / 8 failed** left untouched.

## Risks / follow-ups
- Facade re-exports all *defined* public names + constants, but not incidental
  third-party imports (`json`, `logger`, `get_world_cell`, `settings`, fakes, …).
  No caller uses them; re-add if strict "every module attribute" compatibility is
  ever required (would exceed the 30-line facade budget).
- `client.py` is 203 lines — just over the ~200 soft budget. The 184-line class was
  deliberately left intact; splitting methods would add real behavior risk.
- Smoke runs used temp `--sid-file` paths; `.mock-state/` is gitignored.
