# Refactor Review — AI project (COMPACTED ✅)

**Project:** `D:\AI agent` (Python FastAPI + LangGraph), branch `refactor/compact-ai-backend`.
**Goal:** compact the codebase into small files with **zero behavior change** (clean architecture / OOP / DRY — see `.agents/skills/clean-architecture/SKILL.md`).
**Rule honored:** one module per step, compatibility facades re-exporting the *same* objects, full suite matched **224 passed / 8 failed** (same eight known failures, zero new ones) after every batch. After compaction, the 3 dict-vs-model test bugs were fixed → current baseline **227 passed / 5 failed** (memory-503 tests only).

> The subagents wrote their raw notes into `review.d/*.md`. This file is the merged conversation: each agent's findings, surprises, and verification below.

## Safety net

```
main                    2e03da2  (untouched old committed state)
checkpoint/pre-refactor f28f85c  (ALL pre-refactor work: Docker, NVIDIA, saves, docs)
refactor/compact-ai-backend      (all compaction commits)
```

## Agent round-table (batch 1 — four parallel subagents + orchestrator work)

### 🧩 Combat agent — `scripts/combat_system.py` (465 → 25-line facade)
- Split into `scripts/combat/`: `common.py` (data tables), `damage.py` (165), `defense.py` (76), `status.py` (94), `turn.py` (110).
- **Insight:** no import cycle existed, so no local-import trick was needed (unlike worldgen).
- **Verification:** byte-identity of every moved function vs `git show HEAD`; **500/500 seeded differential calls identical** across all 12 functions; targeted 64 passed / 1 known baseline failure.
- Callers use `from ..scripts import combat_system as _cs` — satisfied by the facade unchanged.

### 💰 XP/loot agent — `scripts/xp_loot.py` (342 → 29-line facade)
- Split into `scripts/economy/`: `common.py` (102), `xp.py` (47), `loot.py` (153), `difficulty.py` (112), `awards.py` (27). One-way graph, no cycles.
- **Insight:** mutable caches (`_enemy_cache`, `_items_db`) had to stay pinned in `common.py` and shared **by reference** — a copy would have broken in-place cache semantics. All 36 caller-imported names re-exported.
- **Verification:** 15 constants + 10 identity checks + **130 function-output comparisons — all passed** vs the original module.

### 🏃 Flee agent — `agents/flee.py` (275 → package with 21-line facade)
- Split into `agents/flee/`: `common.py` (71), `tricks.py` (59), `retaliation.py` (20), `resolve.py` (134).
- **Insight:** tests monkeypatch `flee._roll_d100` / `flee.adjudicate_trick` on the package — `resolve_flee` now resolves those names via a **local import from `.`** so string-path patches still land. `flee.random` re-exported for the same reason.
- **Verification:** 23/23 `test_flee.py`; 47/47 combined targeted suite.

### 🎭 Mock-server agent — `scripts/mock_openrouter_chat.py` (525 → 22-line facade)
- Split into `scripts/mock_chat/`: `common.py` (47), `client.py` (203), `session.py` (128), `cli.py` (136) — one-way chain, no cycles.
- **Insight:** `main`'s argparse description reads `__doc__`, so `cli.py`'s module docstring first line was preserved verbatim.
- **Verification:** deterministic harness → **276-line output identical** (only timestamps differ); `--help` identical; `--say "slay the goblin"` end-to-end exit 0 with intact story/mechanics/state.

### ⚙️ Orchestrator (orchestrator work, not a subagent)
- `engine/orchestrator.py` (287 → 141-line facade + 3 modules): `orchestration/state.py` (141), `graph_run.py` (71), `constants.py`.
- **Insight:** `orch._build_initial_state` is monkeypatched **on instances** in tests — `process_request` must keep calling `self._build_initial_state`, so the method stayed in the class as a delegate.
- **Bug caught:** first mechanical slice dedented `process_request` to module level → 36 failures; fixed by re-indenting, then 42/42 targeted tests green.

### 🔌 Redis client (orchestrator work)
- `redis/client.py` (346 → 21-line facade + 5 modules): `clients/tls.py` (47), `base.py` (125), `input_client.py` (80), `output_client.py` (16), `games_client.py` (105).
- **Critical invariant:** the import-time `_patch_httpx_legacy_tls()` call must fire **before** `upstash_redis` is imported — preserved via `base.py` importing `.tls` first; runtime check: `httpx.Client.__name__ == "_LegacyTLSClient"` ✓.

## Earlier batch (before the round-table)

| Commit | Change | Verification |
|---|---|---|
| `640cec9` | `node4_parallel.py` 673 → 7 modules + facade (same mutable `_SUBNODES` object) | 47/47 targeted |
| `5515aae` | `world_generator.py` 636 → 6 modules + facade (local import breaks patches↔world cycle) | 63/63 targeted |

## Shared lessons (for future agents)

1. Moving one package deeper requires bumping **all** relative imports (`..config` → `...config`), including headers copied verbatim — caused 3 transient failures, all caught by import checks.
2. Compatibility facades must re-export **the same object** (dicts, functions) — tests mutate registries in place and patch by string path.
3. Import cycles are fine if broken with a **local import inside the function** (`worldgen/patches.py`, `flee/resolve.py`).
4. Verify equivalence with a differential harness before claiming done (combat 500/500, xp 130, mock 276-line).
5. Parallel edits to disjoint files are safe; **only the orchestrator runs the full suite and commits**.

## Running log

- 2026-11-19 — skills created in both repos; checkpoint branch + `.gitignore`.
- 2026-11-19 — node4 + worldgen splits committed.
- 2026-11-19 — six more modules compacted in parallel; full suite **224 passed / 8 failed** (exact baseline) → **AI project compaction complete**.

## Merge notes (orchestrator)

All agent reports consolidated above; no conflicts between disjoint file sets. Transient failures observed by agents were caused by other agents' in-progress edits and cleared after completion. Authoritative result at compaction completion: `8 failed, 224 passed in 23.70s` — identical to the pre-refactor baseline. **Follow-up (same day):** fixed the 3 legacy dict-vs-model assertions (`stat_of` helper in tests) → `5 failed, 227 passed in 26.53s`; remaining 5 are memory tests asserting pre-503 behavior.
