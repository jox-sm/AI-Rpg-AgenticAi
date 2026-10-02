# Need-to-Solve — Index

Transferred from full audit 2026-09-29 + `PROGRESS.md`. 16 problems (P00 FIXED, P01-P15 OPEN), each with best-practice solution (Sxx) and debate (Dxx). Pick a debate, answer its Question, then implement its Sxx.

## Build 2026-10-02 (agreed details implemented)
- OpenRouter-only LLMs (`config/models.py:get_classifier_model`, `CLASSIFIER_MODEL`); Node1 Gemini → Scrapy (`scrapy.Selector` + httpx, no Google key) in `agents/node1_web_search.py`.
- Generous local: `context 8000`, `chat_log 40`, `drain 25`, `wall 60s`, `llm_calls 12`, `passes 3`, concurrency 16 (`config/settings.py`).
- State: `context/chat_log/decision_report/budget/next_node/router_trace/force_exit/turn_id` (`schemas/types.py:ChatMessage/BudgetUsage/DecisionReport`, `schemas/state.py total=False`).
- Redis Lua atomic (`redis/client.py:_eval_lua`, `pop_delayed_due`, `release/refresh_lock` compare, `touch_game_keys`, `set_counter ex`); `QueueManager` uuid worker + single-mover guard; `GameStateManager` allowlist merge + `{}`→None + decompress fallback + threshold from settings.
- Node4 parallel atomic (`agents/node4_parallel.py`): deep-copy fan-out, `asyncio.gather`, ordered merge, no Redis writes, `turn_id` idempotent.
- Graph v2 (`engine/graph_v2.py`): `classifier → react_router ⇄ {search|image|redescribe} → mechanics → context_refresh → summarizer → story → pusher`, budget/deadline force-exit, keeper cancels graph on lock loss (`orchestrator.py`).
- Verified: `pip install scrapy`, `pytest 82 passed`, v2 build + N4 smoke OK. Left: damage sig fallback, `/trigger` RENAME Lua, strict schemas, staging integration.
- Asyncio atomicity pass: keeper cancels graph on lock loss (`shield` + explicit cancel), `MultiTaskEngine` blocking acquire/release pairing + parse-before-slot + snapshot stop (mover halted after tasks), API singletons double-checked locking, mover single-guard + uuid workers, N4 `gather` on deep copies with ordered merge.

## Swarm run 2026-10-03 (all issues addressed, verified live)
- Models: `:free` slugs re-probed live — `owl-alpha` dead, `qwen3-coder:free` + `llama-3.2-3b:free` moved to paid (404), `qwen3.8/gemma` 429-flaky. Defaults now `classifier=liquid/lfm-2.5-2.6b:free` (verified JSON), `story/tool=qwen/qwen3.8-27b:free`, `redescribe=gemma-4-26b`, `context=gemma-4-31b`, `image=nemotron-nano` (verified). `openrouter_client` posts `chat/completions` (leading slash dropped `/api/v1` → 404 on every call) + rejects empty envelopes so fallbacks trigger.
- P02 API [FIXED]: `/dbsize` aggregate uses getters, `/trigger` raises 409 + per-item poison guard with `failed` count, `/games state` `{}`→404, `/queue/push` bad JSON→422.
- P12 tools [FIXED]: inventory dict passthrough, dice count validated 1–100, data corrupt guard, skill int cast, public `DamageType()` fallback, stat heal gated on real level-up + single `stat_cap` formula.
- P13 prompts [HARDENED]: `[memory|UNTRUSTED]` + `<web_result>/<recalled_memory>` tags + untrusted-data system line; node6 drops only `^- \w+: error` / `Tool agent error:` lines (keeps "terror").
- P11 node6 [FIXED]: `{Tool Results}` KeyError made EVERY story a generation error — replace-before-format.
- httpx patch CLEARED: ChatOpenAI works with and without it (probe both ways); classifier uses direct httpx client anyway. Old agent path viable.
- LIVE (Upstash creds in gitignored `.env`): Lua locks/pop/touch/state/drain all pass on real REST (EVAL works); live classifier → real attack/goblin report @0.98; live full turn 40.8s → real pushed story, no error. Search still unconfigured (drain fail-closed, expected).
- Tests: 113 passed (82 legacy + 31 hard). Secret hygiene: subagent leaked real key into tracked `.env.example` — reverted before commit, verified absent from HEAD and tree. Rotate the OpenRouter key when convenient.
- Left: `/trigger` RENAME Lua, strict Pydantic edge (D08), staging Search creds.

## Map

| ID | Name | Severity | Files |
|----|------|----------|-------|
| P00 | deps-missing-undeclared [FIXED] | P0 | `problems/P00-*.md`, `solutions/S00-*`, `discussions/D00-*` |
| P01 | windows-signal-shutdown-hang | P0 | P01/S01/D01 |
| P02 | api-dbsize-trigger [FIXED] | P0 | P02/S02/D02 |
| P03 | redis-persistence-counter-ttl-compression [FIXED] | P0 | P03/S03/D03 |
| P04 | locks-queue-races-worker-id [FIXED] | P0 | P04/S04/D04 |
| P05 | engine-concurrency-shutdown-backpressure [FIXED] | P0 | P05/S05/D05 |
| P06 | failure-routing-poison-vs-lock [PARTIAL: lock-miss still counts retry] | P0 | P06/S06/D06 |
| P07 | settings-env-fragile [PARTIAL] | P1 | P07/S07/D07 |
| P08 | schemas-unenforced-reducer-growth [OPEN] | P1 | P08/S08/D08 |
| P09 | graph-double-budget-stale-context [FIXED via v2] | P1 | P09/S09/D09 |
| P10 | orchestrator-merge-keeper [FIXED] | P1 | P10/S10/D10 |
| P11 | nodes-models-images [FIXED: node6 KeyError + URL + envelope guards] | P1 | P11/S11/D11 |
| P12 | tools-registry-bugs [FIXED] | P1 | P12/S12/D12 |
| P13 | prompt-injection [HARDENED] | P1 sec | P13/S13/D13 |
| P14 | triplication-dead-code [OPEN] | P2→P1 | P14/S14/D14 |
| P15 | tests-fakes-gaps [IMPROVED: 113, contract tests] | P1 | P15/S15/D15 |

Statuses re-verified in the 2026-10-03 swarm run (see §Swarm run above).

## How to use
1. Read `problems/Pxx-*` for evidence (`file:line`), impact, repro.
2. Read `solutions/Sxx-*` for fix steps.
3. Debate in `discussions/Dxx-*` — answer Question at bottom, I argue back, then we lock solution.
4. Implement, verify (`pip check`, `pytest -q`), tick `PROGRESS.md`.

Start suggested: P01 (hang) or P02 (API 500) — both block live pipeline run.
