# P11 — Nodes: Try Gaps + Model/Token Drift + Image Grid Truncation

Status: OPEN. Severity P1.

## Description
All 7 nodes have outer try, but `state['uuid']`, `get_openrouter_direct()`, `state["images"].items()` outside try (`node2:56,62,65`, `node3:32,39`, `node5:36,38`, `node6:65,67`, `agent.py:153`) -> KeyError bypasses fallback. `node1:24-38` returns `"Search unavailable: ..."` as success string stored at `:64`, injected as lore at `agent.py:191`, `node6:94`. `node7:19` unguarded `model_dump()`.
Factory bypass with divergent `max_tokens`: node2 `8192 vs 4096` (`models.py:35-36`), node3 `65536 vs 32768` (`:39-40`, 64K over free limits), node5 `2048 vs 4096` (`:47-48`), node6 `8192 vs 16384` (`:51`). Only node1/node4 use factories. Defaults all `:free`/`owl-alpha` (`settings.py:50-54`).
`openrouter_client.py:13-51,69-85`: `raise_for_status` no retry for 429/502, hardcoded `timeout 120` ignores `request_timeout`, singleton never closed, `Bearer None` if key missing, unchecked `result["choices"][0]["message"]["content"]` (`node2:82`, `node3:64`, `node5:79`, `node6:128`), `response_format json_object` ignored by free models, single `json.loads` no fence-strip/repair.
Grid: `node2:38-52 _generate_empty_grid` dead, `:83,89` assumes dict (list/`{"grid":[...]}` -> AttributeError), `:92,94` `o.lower()` crashes on dict, arbitrary `terrain` -> `GridCell ValidationError` poisons 224 cells, `8192` tokens cannot fit 225 cells (~15-20K) -> truncation guarantees `json.loads` fail, `:102` mutates `image_data.grid` bypassing reducer, per-image `except log-drop :104-105` partial dict no error flag. `node3:67-84` fans single `parsed` to every image -> multi-image identical. `node3:86-93` success no `error` key vs fail has it. Entry Node5 first (`graph_builder:111-112`) so router can't use fresh mechanics.

## Evidence
- `rpg_ai_server/agents/node*.py`, `node4_tool_agent/agent.py:124-217`, `utils/openrouter_client.py:13-85`, `config/models.py:35-51`, `config/settings.py:50-54`

## Impact
Top live-pipeline risk: silent empty grids, `(generation error)` stories, free-tier 429s with no fallback.

## Repro
Push image turn with free model 429 -> `grid_data={}` no flag. 225-cell prompt -> truncated JSON fail.

## Related
S11, D11, P09.
