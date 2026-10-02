# S08 — Schemas: Validate at Edge, Bound Reducers

Best practice:
- `GameRequest.uuid: UUID4`, `timestamp: PositiveFloat`, `images: List[ImageData]` (not dicts). `DiceRoll` `model_validator` forbids `adv+dis`, checks `total==sum+mod`. `CharacterStats` `ge=0`, `health<=max_health`, `skills conint(ge=0,le=20)`, `resistances confloat(ge=0,le=1)`. `quantity: PositiveInt`, `durability<=max`. `ContextSummary` truncate in validator, not raise.
- `GameState(Total=False)` + `required` subset, or split `RequestState` vs `PersistedState`. Reducers: use `operator.add` only for `tool_results` with cap `[-50:]`, others overwrite (`lambda a,b: b`). Rename `__next__` -> `next_node: Literal[...]`.
- Enforce in `redis_api.py` with `response_model=GameOutput`, `request_model` per route. Engine parses `GameRequest` once at dequeue.
