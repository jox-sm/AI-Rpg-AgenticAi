"""Graph v2 tests: budget terminators, ReAct routing, context caps. No LLM calls."""

import asyncio

from rpg_ai_server.config.settings import settings
from rpg_ai_server.engine.graph_v2 import (
    _budget_exhausted,
    build_game_graph_v2,
    context_refresh_node,
    react_router_node,
    route_react,
)
from tests.fakes import FakeOutputClient


def _run(coro):
    return asyncio.run(coro)


def _state(**kw):
    s = {
        "conditional_passes": 0,
        "budget": {"llm_calls": 0, "tokens_est": 0, "started_at": 0.0},
        "router_trace": [],
        "needs_search": False,
        "needs_image_processing": False,
        "needs_re_description": False,
        "decision_report": {},
    }
    s.update(kw)
    return s


def test_budget_forces_story_on_max_passes():
    s = _state(conditional_passes=settings.app.router_max_passes - 1,
               needs_search=True)  # work remains, budget wins
    out = _run(react_router_node(s))
    assert out["next_node"] == "story"
    assert out["force_exit_reason"] == "max_passes"
    assert out["router_trace"][-1]["tool"] == "force_story"


def test_budget_forces_story_on_llm_cap():
    s = _state(budget={"llm_calls": settings.app.max_llm_calls_per_turn,
                       "tokens_est": 0, "started_at": 0.0})
    out = _run(react_router_node(s))
    assert out["next_node"] == "story"
    assert out["force_exit_reason"] == "max_llm_calls"


def test_router_serves_search_then_image_across_passes():
    # Multi-node turn: search first, image still pending → back to router, not mechanics.
    s = _state(needs_search=True, needs_image_processing=True,
               decision_report={"reason": "t", "needs_search": True, "needs_image": True})
    first = _run(react_router_node(s))
    assert first["next_node"] == "search"
    s2 = _state(conditional_passes=1, needs_search=False, needs_image_processing=True,
                decision_report={"reason": "t"})
    second = _run(react_router_node(s2))
    assert second["next_node"] == "image"
    assert len(second["router_trace"]) == 1  # trace is per-visit; engine accumulates


def test_router_defaults_to_mechanics_and_rejects_unknown():
    assert _run(react_router_node(_state()))["next_node"] == "mechanics"
    assert route_react({"next_node": "bogus"}) == "mechanics"
    assert route_react({"next_node": "story"}) == "story"


def test_context_refresh_caps_and_appends_fresh_mechanics():
    cap = settings.app.context_max_chars
    old = "x" * (cap + 500)
    out = _run(context_refresh_node({
        "context": old,
        "decision_report": {"intent": "attack"},
        "tool_results": ["dice conquer"],
    }))
    assert len(out["context"]) <= cap
    assert "attack" in out["context"]
    assert out["context"].endswith("dice conquer"[-800:])


def test_graph_v2_builds_and_compiles():
    from rpg_ai_server.redis.output_cache import OutputCache
    wf = build_game_graph_v2(OutputCache(FakeOutputClient()))
    compiled = wf.compile()
    assert compiled is not None
