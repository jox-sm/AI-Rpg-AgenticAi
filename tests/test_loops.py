import asyncio

from rpg_ai_server.config.settings import settings
from rpg_ai_server.engine.graph_builder import make_router_node, route_from_conditional


def _run(coro):
    return asyncio.run(coro)


def _state(**overrides):
    state = {
        "uuid": "u1",
        "needs_search": False,
        "needs_image_processing": False,
        "needs_re_description": False,
        "conditional_passes": 0,
        "remaining_steps": settings.app.loop_recursion_limit,
        "__next__": "node4_tool_agent",
    }
    state.update(overrides)
    return state


def test_router_routes_to_search():
    node = make_router_node(None)
    out = _run(node(_state(needs_search=True)))
    assert out["__next__"] == "node1_web_search"
    assert out["conditional_passes"] == 1


def test_router_routes_to_image():
    node = make_router_node(None)
    out = _run(node(_state(needs_image_processing=True)))
    assert out["__next__"] == "node2_image_processor"


def test_router_routes_to_redescriptor():
    node = make_router_node(None)
    out = _run(node(_state(needs_re_description=True)))
    assert out["__next__"] == "node3_redescriptor"


def test_router_defaults_to_main_pipeline():
    node = make_router_node(None)
    out = _run(node(_state()))
    assert out["__next__"] == "node4_tool_agent"


def test_router_precedence_search_over_image():
    node = make_router_node(None)
    out = _run(node(_state(needs_search=True, needs_image_processing=True)))
    assert out["__next__"] == "node1_web_search"


def test_router_increments_passes_and_decrements_steps():
    node = make_router_node(None)
    out = _run(node(_state()))
    assert out["conditional_passes"] == 1
    assert out["remaining_steps"] == settings.app.loop_recursion_limit - 1


def test_router_cap_forces_main_pipeline_and_clears_flags():
    node = make_router_node(None)
    max_passes = settings.app.router_max_passes
    out = _run(node(_state(needs_search=True, conditional_passes=max_passes - 1)))
    assert out["__next__"] == "node4_tool_agent"
    assert out["needs_search"] is False
    assert out["needs_image_processing"] is False
    assert out["needs_re_description"] is False


def test_router_remaining_steps_degradation():
    node = make_router_node(None)
    out = _run(node(_state(needs_search=True, remaining_steps=settings.app.remaining_steps_min + 1)))
    assert out["__next__"] == "node4_tool_agent"


def test_route_from_conditional_backs_off_when_steps_low():
    assert route_from_conditional(_state(needs_search=True, remaining_steps=5)) == "node4_tool_agent"


def test_route_from_conditional_returns_router_when_flag_set():
    assert route_from_conditional(_state(needs_search=True)) == "router"


def test_route_from_conditional_returns_main_when_clear():
    assert route_from_conditional(_state()) == "node4_tool_agent"