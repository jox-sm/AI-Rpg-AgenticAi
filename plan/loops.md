# Loop Engineering & Debugging

Every agent system is a while loop around an LLM: **reason → act → observe → repeat, until a stop condition**. The quality of the system lives in the loop — how it terminates, what it remembers, and how it degrades. This doc maps that theory onto RPG AI Quest's actual graph and audits it.

Sources: Agentic Thinking "The Loop" series, LangGraph docs (recursion limit, RemainingSteps, GraphRecursionError), Oracle/IBM/Google loop-engineering references, and real-world LangGraph loop failures (langchain/langgraph#148, #6731).

---

## 1. The loops in this system

| Loop | Where (code) | Shape | Terminator today | Risk |
|------|--------------|-------|------------------|------|
| **Turn loop** (player action → worker → response) | `orchestrator.process_request()` + `multi_tasker.py` | conditional loop, human-gated | Player exits / `game_over` (exit popup = **human terminator**) | low — human always ends it |
| **Router cycle** (node1/2/3 → router → nodeX) | `graph_builder.py` lines 94–108 | fan-out conditional (max 3 passes) | **verified gap**: each node clears its own `needs_*` flag | 🟡 medium — bounded today, but nothing defends against cross-triggering |
| **node4 ReAct loop** (think → act → observe) | `agents/node4_tool_agent/agent.py` `create_agent(...)` | bounded loop | LangGraph default `recursion_limit` only | 🔴 high — a model that keeps calling tools burns tokens to the limit |
| **Queue retry loop** | `redis/queue.py` `QueueManager` | bounded loop (3 attempts + backoff) | budget (count) + DLQ ledger | low — already correct |

The first two bullets are the whole game: **the player is the verified-gap terminator** of the outer loop. Everything below is the machinery that must not run away.

---

## 2. The atom: reason → act → observe

Every loop here is the same cell repeated:

```
Thought → Action (tool call) → Observation → Thought → ... → final answer
```

- **node4** is the pure ReAct atom (`create_agent` = model ↔ 9 tools).
- **The router cycle** is ReAct at graph level: the "action" is running node1/2/3, the "observation" is the state it mutates, and `route_from_conditional` is the router that decides whether to loop back.
- **The turn loop** is the same atom over turns: the player's action is the input, the story output is the observation, the memory drain is what persists it.

---

## 3. Termination — loop on the verified gap, not the try-count

Rule from the field: stop when an **independent, checkable condition** closes ("verified gap"), and use **budgets only as backstops**. Never stop solely on "the model said done" or "we tried N times".

### 3.1 Turn loop — ✅ already correct (human terminator)
Exit popup + scenario registry = human-gated loop. No change.

### 3.2 Router cycle — 🟡 bounded today, guard it anyway
Verified gap already exists: each conditional node **clears its own flag on every return path** (`node1_web_search.py:71` `needs_search: False`, node2/node3 likewise), so the cycle self-terminates after ≤3 passes (one per flag).

Residual hazards that make a defensive cap worthwhile:
1. **Cross-triggering**: nothing stops a future node from *setting another node's flag* (e.g. node3 decides an image needs reprocessing). One stray `needs_search: True` turns the bounded fan-out into a genuine cycle.
2. **Model-driven flags**: `needs_re_description`/`needs_search` are set by model output — a model could re-assert them on the next turn's state.
3. No explicit `recursion_limit` config — the default is the only backstop.

Fix (defensive, state-driven):
```python
# state: add "conditional_passes": 0  — the cap lives in the ROUTER NODE (a conditional
# edge function can only route, it cannot update state)
async def router_node(state: GameState) -> Dict[str, Any]:
    needs = (state.get("needs_search")
             or state.get("needs_image_processing")
             or state.get("needs_re_description"))
    if needs and state.get("conditional_passes", 0) >= 4:
        # cap hit: clear all flags and fall through to the main pipeline
        return {"__next__": "node4_tool_agent",
                "conditional_passes": 0,
                "needs_search": False,
                "needs_image_processing": False,
                "needs_re_description": False}
    if needs:
        return {"__next__": <routed node>, "conditional_passes": state.get("conditional_passes", 0) + 1}
    return {"__next__": "node4_tool_agent", "conditional_passes": 0}
```
4 passes = entry + one pass per flag (the legitimate max). Hitting the cap resets and clears — a genuine flip-flop cycle (node1 sets `needs_image_processing`, node2 sets `needs_search`…) becomes a graceful fallthrough to node4 instead of an exploding loop or a `GraphRecursionError` with stale flags on the next turn.

### 3.3 node4 ReAct — ✅ keep model freedom, add budget backstops
The agent's "done" is self-graded ("Return a summary of all changes made" — the model judges its own completeness). That's acceptable for a bounded, low-stakes per-turn step, but it needs hard backstops (see §4).

### 3.4 Queue retry — ✅ already a budget loop with a ledger
3 attempts + backoff + DLQ = "budget as backstop, dead letter as ledger". Keep as-is.

---

## 4. Budget backstops (all loops must have all of these)

### 4.1 `recursion_limit` on every `ainvoke`
`orchestrator.py:129` calls `self.compiled_graph.ainvoke(initial_state)` with **no config**. LangGraph default is 25 (or 1000 in ≥1.0.6) — never rely on it. Set it explicitly and treat hitting it as a catchable condition:

```python
try:
    result = await self.compiled_graph.ainvoke(
        initial_state, config={"recursion_limit": 60}
    )
except GraphRecursionError:
    logger.error(f"Graph hit recursion limit for {request.uuid}")
    return {
        "uuid": request.uuid,
        "game_data": request.data,
        "story": "The story grows quiet — the weave of fate catches. Try again.",
        "error": "recursion_limit",
    }
```
60 supersteps ≈ 3× the worst legitimate pipeline (router passes ×2 + node4 iterations + nodes). This is the **smoke detector**, not the thermostat.

### 4.2 Proactive degradation with `RemainingSteps`
Better than catching the throw: `RemainingSteps` is auto-populated per node. In `route_from_conditional`, degrade before the limit:

```python
if state.get("remaining_steps", 100) <= 10:
    return "node4_tool_agent"   # stop looping, finish the pipeline best-effort
```
Graceful completion beats a raised error.

### 4.3 Tool-call budget in node4 (`ToolCallLimitMiddleware`)
`create_agent` supports middleware. Bound the ReAct loop in units that matter (LLM calls / tool calls), not supersteps:

```python
from langchain.agents.middleware import ToolCallLimitMiddleware

agent = create_agent(
    model=get_tool_agent_model(),
    tools=[...],
    system_prompt=TOOL_AGENT_SYSTEM_PROMPT,
    checkpointer=MemorySaver(),
    middleware=[ToolCallLimitMiddleware(max_total_tool_calls=15, on_limit="return_last_observation")],
)
```
Typical turn = 2–6 tool calls (situational_dice → dice_roller → damage → stats → cooldowns). 15 = healthy headroom, hard ceiling.

### 4.4 Futile-action (duplicate) detection
Real-world failure (langgraph#6731): tool errors in a loop — the model retries the same failing call with slight variations until the limit. Add a tiny guard inside node4: keep the last 6 tool-call signatures in state; if the **same tool + same args appears 3×**, stop calling and return what we have:

```python
signature = f"{tool_name}({sorted(args.items())})"
if signature in recent[-6:] and signature in recent[-6:-3]:
    break  # futile loop — degrade, don't retry
```

### 4.5 Wall-clock budget
A tight loop burns wall time fastest. Wrap the whole `process_request` in a timeout (e.g. 120s; the SSE client already tolerates ~30–60s per turn). Abort → return partial + `error: timeout`.

### 4.6 Token budget (optional later)
Cumulative token check in the same middleware chain — skip for now; free-tier models make this a later optimization.

---

## 5. Memory axis — fresh context per iteration ✅ (already right)

The loop theory says: **throw away context every iteration; disk/files are the memory.** RPG AI Quest already does this correctly:

- node4 gets a **compressed summary** (`context_summary`, `search_results[:2000]`) — not the full message history.
- Long-term memory = **Upstash Vector** (the "files"), queried top_k=5, injected as `PREVIOUS MEMORIES`.
- Redis state stores **gzip-compressed** story/incidents.

The regression to watch: never let node4 accumulate full chat history across turns (self-graded loops with accumulating context = the danger zone). The checkpointer `MemorySaver()` is recreated per request — keep it that way; do NOT promote it to a cross-turn checkpointer.

## 6. Grader axis — move "done" outside the model where possible

| Check | Grader | Status |
|-------|--------|--------|
| "All mechanics processed" (node4) | model (self) | acceptable, bounded — keep |
| Story coherence / output validity (node6 → node7) | pipeline shape | **add**: node6 must assert `story_output` non-empty + state deltas present; else mark `status=error` |
| Action classification + gain/loss patterns | **incident learning** (`scripts/incident_learning.py`) | ✅ external grader — expand it |
| "Is the game fun / should it continue" | player | ✅ human grader — exit popup |
| Memory recall quality | vector top_k hits vs. actual events | 🟡 nice-to-have: log recall hits per turn (tracing) |

## 7. Debugging the loops

LangGraph is a state machine — a flat log can't show loop bugs. Requirements:

1. **Node-level tracing** — LangSmith (`LANGCHAIN_TRACING_V2=true` + project key) or a callback handler emitting one span per node with input/output state. The bug lives in the **state diff between nodes**, not the model call.
2. **Stream while developing** — `graph.stream(initial_state, stream_mode="updates")` prints which node ran and what it returned, in order. The fastest loop debugger.
3. **Inspect state at any point** — with a checkpointer, `get_state()`/`get_state_history()` shows `state.next` and metadata; the router-cycle fix can be verified this way.
4. **Temporary debug nodes** — log `state["needs_*"]` + `conditional_passes` inside `route_from_conditional` until the cycle is proven dead. Remove before prod.

### Symptom → cause table

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Loop forever → GraphRecursionError | conditional never routes to END; exit condition watches state the loop doesn't change | §3.2 flag clearing + passes cap; RemainingSteps degradation |
| Stops after 1 step (premature "done") | edge returns END too early; node4 self-grades "done" without tool calls | §6 external checks |
| Same tool called repeatedly with identical args | futile-action loop (model can't consume a tool error) | §4.4 duplicate guard |
| Works locally, loops in prod | in-memory state wiped → flags re-evaluated per fresh state | keep Redis state as source of truth; checkpointer per-request only |
| `state` appears empty | node returned `None` instead of a dict | audit: every node returns a `Dict[str, Any]` |

---

## 8. Concrete change list (mapped to code)

| # | Change | File |
|---|--------|------|
| L1 | Add `conditional_passes` to `GameState` schema, init 0 | `schemas/state.py`, `engine/orchestrator.py` |
| L2 | Router cap: increment `conditional_passes` per pass; on cap hit (4) clear all `needs_*` flags + fall through to node4; `RemainingSteps` degradation in `route_from_conditional` | `engine/graph_builder.py` |
| L3 | (already done — no change) node1/2/3 clear their own `needs_*` flags after processing | `agents/node1_web_search.py` etc. |
| L4 | `ainvoke` with `config={"recursion_limit": 60}` + `except GraphRecursionError` graceful output | `engine/orchestrator.py:129` |
| L5 | `ToolCallLimitMiddleware(max_total_tool_calls=15)` in `create_agent` | `agents/node4_tool_agent/agent.py` |
| L6 | Futile-action guard (last-6 signature window, 3 repeats → stop) | `agents/node4_tool_agent/agent.py` |
| L7 | Wall-clock timeout around `process_request` (120s) → partial + `error: timeout` | `engine/orchestrator.py`, `engine/multi_tasker.py` |
| L8 | node6 asserts output validity (non-empty story, state deltas) | `agents/node6_story_generator.py` |
| L9 | LangSmith tracing env vars in `.env.example`; stream-based dev loop | repo + docs |
| L10 | Test: router flip-flop simulation (node1 sets `needs_image_processing` forever → assert graph still completes ≤4 passes) | tests |

---

## 9. What this validates in the existing plans

- The **memory design is already loop-optimized** (fresh context per iteration, vector store as external memory) — §5 confirms it, don't regress it.
- The **drain every 10 messages** is the loop's "ledger write" — the spine that keeps iterations independent. Keep it at turn granularity.
- The **exit popup (human terminator)** is the only loop that should rely on a human — everything else gets verified gaps + budgets from §3–4.
- Incident learning = the system's external grader → feed it loop metrics (recall hits, futile loops) to improve the game.
