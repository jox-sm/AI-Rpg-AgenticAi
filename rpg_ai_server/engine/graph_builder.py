from __future__ import annotations

from typing import Any, Dict, Literal

from langgraph.graph import END, START, StateGraph

from ..agents.node1_web_search import node1_web_search
from ..agents.node2_image_processor import node2_image_processor
from ..agents.node3_redescriptor import node3_redescriptor
from ..agents.node4_tool_agent import node4_tool_agent
from ..agents.node5_context_injector import node5_context_injector
from ..agents.node6_story_generator import node6_story_generator
from ..agents.node7_output_pusher import node7_output_pusher
from ..redis.output_cache import OutputCache
from ..schemas.state import GameState
from ..config.settings import settings
from ..utils.logger import logger


def make_router_node(output_cache: OutputCache):
    async def router_node(state: GameState) -> Dict[str, Any]:
        logger.info(f"[Router] Evaluating state for UUID {state['uuid']}")

        passes = state.get("conditional_passes", 0) + 1
        remaining = state.get("remaining_steps", settings.app.loop_recursion_limit) - 1
        exhausted = (
            passes >= settings.app.router_max_passes
            or remaining <= settings.app.remaining_steps_min
        )

        if exhausted:
            logger.warning(
                f"[Router] Loop budget exhausted for UUID {state['uuid']} "
                f"(passes={passes}, remaining={remaining}), forcing main pipeline"
            )
            return {
                "conditional_passes": passes,
                "remaining_steps": remaining,
                "needs_search": False,
                "needs_image_processing": False,
                "needs_re_description": False,
                "__next__": "node4_tool_agent",
            }

        decision: Dict[str, Any] = {
            "conditional_passes": passes,
            "remaining_steps": remaining,
        }

        if state.get("needs_search"):
            logger.info(f"[Router] Routing to web search for UUID {state['uuid']}")
            decision["__next__"] = "node1_web_search"
            return decision

        if state.get("needs_image_processing"):
            logger.info(f"[Router] Routing to image processor for UUID {state['uuid']}")
            decision["__next__"] = "node2_image_processor"
            return decision

        if state.get("needs_re_description"):
            logger.info(f"[Router] Routing to re-descriptor for UUID {state['uuid']}")
            decision["__next__"] = "node3_redescriptor"
            return decision

        logger.info(f"[Router] No conditionals needed, continuing main pipeline for UUID {state['uuid']}")
        decision["__next__"] = "node4_tool_agent"
        return decision

    return router_node


def route_from_router(state: GameState) -> Literal[
    "node1_web_search",
    "node2_image_processor",
    "node3_redescriptor",
    "node4_tool_agent",
]:
    return state.get("__next__", "node4_tool_agent")


def route_from_conditional(state: GameState) -> Literal["router", "node4_tool_agent"]:
    if state.get("remaining_steps", settings.app.loop_recursion_limit) <= settings.app.remaining_steps_min:
        return "node4_tool_agent"
    if (
        state.get("needs_search")
        or state.get("needs_image_processing")
        or state.get("needs_re_description")
    ):
        return "router"
    return "node4_tool_agent"


def build_game_graph(output_cache: OutputCache) -> StateGraph:
    logger.info("Building game graph...")

    workflow = StateGraph(GameState)

    workflow.add_node("router", make_router_node(output_cache))
    workflow.add_node("node1_web_search", node1_web_search)
    workflow.add_node("node2_image_processor", node2_image_processor)
    workflow.add_node("node3_redescriptor", node3_redescriptor)
    workflow.add_node("node4_tool_agent", node4_tool_agent)
    workflow.add_node("node5_context_injector", node5_context_injector)
    workflow.add_node("node6_story_generator", node6_story_generator)

    async def output_pusher_wrapper(state: GameState) -> Dict[str, Any]:
        return await node7_output_pusher(state, output_cache)

    workflow.add_node("node7_output_pusher", output_pusher_wrapper)

    workflow.add_edge(START, "node5_context_injector")
    workflow.add_edge("node5_context_injector", "router")

    workflow.add_conditional_edges(
        "router",
        route_from_router,
        {
            "node1_web_search": "node1_web_search",
            "node2_image_processor": "node2_image_processor",
            "node3_redescriptor": "node3_redescriptor",
            "node4_tool_agent": "node4_tool_agent",
        },
    )

    workflow.add_conditional_edges(
        "node1_web_search",
        route_from_conditional,
        {"router": "router", "node4_tool_agent": "node4_tool_agent"},
    )
    workflow.add_conditional_edges(
        "node2_image_processor",
        route_from_conditional,
        {"router": "router", "node4_tool_agent": "node4_tool_agent"},
    )
    workflow.add_conditional_edges(
        "node3_redescriptor",
        route_from_conditional,
        {"router": "router", "node4_tool_agent": "node4_tool_agent"},
    )

    workflow.add_edge("node4_tool_agent", "node6_story_generator")
    workflow.add_edge("node6_story_generator", "node7_output_pusher")
    workflow.add_edge("node7_output_pusher", END)

    logger.info("Game graph built successfully")
    return workflow
