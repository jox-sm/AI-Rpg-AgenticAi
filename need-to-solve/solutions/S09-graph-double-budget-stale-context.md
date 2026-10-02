# S09 — Graph: Single Budget, Fresh Context, Explicit Edges

Best practice:
- Single budget: `max_passes=4`, decrement per router visit, `remaining_steps` derived (`passes_left*7`), no separate LangGraph `recursion_limit` mismatch (set `recursion_limit = passes*10`).
- `make_router_node()` pure (no cache arg). `route_*` return `Literal`, raise on unknown, never default to node4 silently.
- Order: `START->router->(N5 once)->[N1/2/3 loop]->N4->N5_refresh(light)->N6->N7->END`. Add `N5_refresh` (200 tokens) after mechanics so story sees fresh summary.
- `compile(checkpointer=MemorySaver())` if keeping LangGraph, else drop to `async def pipeline(state)` with `for _ in range(max_passes)` — shorter, no dunder.
- Rename `__next__` -> `next_node`.
