# P09 — Graph Double Budget + Stale Context + Dead Edges

Status: OPEN. Severity P1.

## Description
`engine/graph_builder.py:20-146`: `make_router_node(output_cache)` takes cache never used `:20-69`. Two budgets: LangGraph `recursion_limit=60` (`orchestrator.py:191`, `settings.py:66`) counts every node, app `router_max_passes=4 + remaining_steps 60 floor 10 (:67,70)`. Router exhaust `:26-29` after ~4 passes forces `__next__=node4`; LangGraph 60 allows 6-10 traversals — whichever fires first wins, `GraphRecursionError` then swallowed (P06). `route_from_conditional :81-90` ignores `conditional_passes`, checks `remaining<=10` only -> almost never fires (60-4=56). `route_from_router :72-78` defaults missing `__next__` to `node4` silently. Wiring `:111-112 START->node5->router` runs Node5 once, conditionals `:125-139 N1/2/3->router` never re-invoke Node5 -> context stale after web/image. Linear `:141-143 node4->node6->node7->END` no error edge. Dunder `__next__` risks LangGraph collision; `orchestrator.py:93` sets, `:36-43,52,66` overwrite. `compile()` with no checkpointer `:39` -> manual persistence only.

## Evidence
- `rpg_ai_server/engine/graph_builder.py:20-146`, `engine/orchestrator.py:39,93,191`, `config/settings.py:66-70`

## Impact
Unpredictable routing, stale summary to story generator, silent misroute on router bug, harder debug.

## Repro
Log `conditional_passes/remaining_steps/__next__` per router visit -> see 56 remaining when forced, `route_from_conditional` never taken.

## Related
S09, D09, P08, P10.
