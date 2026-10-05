"""Router loop guards (v2 ReAct): priority, re-entrancy, budget force-exits."""

import asyncio
import time

from rpg_ai_server.config.settings import settings
from rpg_ai_server.engine.graph_v2 import (
    _budget_exhausted,
    react_router_node,
    route_react,
)


def _run(coro):
    return asyncio.run(coro)


def _state(**overrides):
    state = {
        "uuid": "u1",
        "needs_search": False,
        "needs_image_processing": False,
        "needs_re_description": False,
        "conditional_passes": 0,
        "budget": {"llm_calls": 0, "tokens_est": 0, "started_at": 0.0},
        "router_trace": [],
        "decision_report": {"reason": "t"},
    }
    state.update(overrides)
    return state


def test_router_priority_search_over_image_over_redescribe():
    out = _run(react_router_node(_state(needs_search=True, needs_image_processing=True,
                                        needs_re_description=True)))
    assert out["next_node"] == "search"
    out = _run(react_router_node(_state(needs_image_processing=True, needs_re_description=True)))
    assert out["next_node"] == "image"
    out = _run(react_router_node(_state(needs_re_description=True)))
    assert out["next_node"] == "redescribe"


def test_router_defaults_to_mechanics_and_counts_passes():
    out = _run(react_router_node(_state()))
    assert out["next_node"] == "mechanics"
    assert out["conditional_passes"] == 1
    assert out["router_trace"][-1]["step"] == 1


def test_router_trace_carries_tool_and_reason():
    out = _run(react_router_node(_state(needs_search=True)))
    (entry,) = out["router_trace"]
    assert entry["tool"] == "search" and entry["reason"] == "t"


def test_budget_deadline_forces_story():
    old = {"llm_calls": 0, "tokens_est": 0,
           "started_at": time.time() - settings.app.request_timeout_seconds - 1}
    out = _run(react_router_node(_state(budget=old, needs_search=True)))
    assert out["next_node"] == "story"
    assert out["force_exit_reason"] == "deadline"


def test_budget_ok_when_fresh():
    assert _budget_exhausted(_state()) is None


def test_route_react_maps_and_rejects_unknown():
    assert route_react({"next_node": "search"}) == "search"
    assert route_react({"next_node": "image"}) == "image"
    assert route_react({"next_node": "redescribe"}) == "redescribe"
    assert route_react({"next_node": "mechanics"}) == "mechanics"
    assert route_react({"next_node": "story"}) == "story"
    assert route_react({"next_node": "bogus"}) == "mechanics"
    assert route_react({}) == "mechanics"
