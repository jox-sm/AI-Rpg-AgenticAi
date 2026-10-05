from __future__ import annotations

import time
from typing import Any, Dict, Literal

from langgraph.graph import END, START, StateGraph

from ..agents.classifier import classifier_node
from ..agents.node0_worldgen import node0_worldgen
from ..agents.node1_web_search import node1_web_search
from ..agents.node2_image_processor import node2_image_processor
from ..agents.node3_redescriptor import node3_redescriptor
from ..agents.node4_parallel import node4_parallel
from ..agents.node5_context_injector import node5_context_injector
from ..agents.node6_story_generator import node6_story_generator
from ..agents.node7_output_pusher import node7_output_pusher
from ..config.settings import settings
from ..redis.output_cache import OutputCache
from ..schemas.state import GameState
from ..utils.logger import logger


def _budget_exhausted(state: GameState) -> str | None:
    b = state.get("budget") or {}
    calls = int(b.get("llm_calls", 0) or 0)
    started = float(b.get("started_at", 0.0) or 0.0)
    elapsed = (time.time() - started) if started else 0.0
    if int(state.get("conditional_passes", 0) or 0) >= settings.app.router_max_passes:
        return "max_passes"
    if calls >= settings.app.max_llm_calls_per_turn:
        return "max_llm_calls"
    if elapsed >= settings.app.request_timeout_seconds:
        return "deadline"
    return None


async def react_router_node(state: GameState) -> Dict[str, Any]:
    """ReAct router: multi-node capable, budget-first terminators.

    Decides next_node among search|image|redescribe|mechanics|story.
    Terminates when classifier says done OR cost/latency met (force to story).
    """
    passes = int(state.get("conditional_passes", 0) or 0) + 1
    upd: Dict[str, Any] = {"conditional_passes": passes}
    forced = _budget_exhausted({**state, "conditional_passes": passes})
    trace = list(state.get("router_trace", []) or [])
    if forced:
        upd.update({
            "next_node": "story",
            "force_exit_reason": forced,
            "router_trace": trace + [{"step": passes, "tool": "force_story", "reason": forced}],
        })
        logger.warning(f"[ReAct] force exit ({forced}) pass={passes}")
        return upd
    rep = state.get("decision_report") or {}
    need_s = bool(state.get("needs_search") or (rep.get("needs_search") if isinstance(rep, dict) else False))
    need_i = bool(state.get("needs_image_processing") or (rep.get("needs_image") if isinstance(rep, dict) else False))
    need_r = bool(state.get("needs_re_description") or (rep.get("needs_redescribe") if isinstance(rep, dict) else False))
    # Priority but re-entrant: after each tool, flags cleared, router re-evaluates
    # so image+search both happen across passes (was single-shot).
    if need_s:
        nxt = "search"
    elif need_i:
        nxt = "image"
    elif need_r:
        nxt = "redescribe"
    else:
        nxt = "mechanics"
    reason = rep.get("reason", "react") if isinstance(rep, dict) else "react"
    upd.update({
        "next_node": nxt,
        "router_trace": trace + [{"step": passes, "tool": nxt, "reason": reason}],
    })
    logger.info(f"[ReAct] pass={passes} -> {nxt}")
    return upd


def route_react(state: GameState) -> Literal["search", "image", "redescribe", "mechanics", "story"]:
    nxt = state.get("next_node", "mechanics")
    if nxt not in ("search", "image", "redescribe", "mechanics", "story"):
        return "mechanics"
    return nxt  # type: ignore[return-value]


async def context_refresh_node(state: GameState) -> Dict[str, Any]:
    """Update rolling context:string (cap generous 8000) + chat log cap 40.

    Runs AFTER mechanics so story sees fresh results (was stale N5-first).
    Pure string op, no LLM (cheap) — full N5 injector still runs at entry.
    """
    try:
        cap = settings.app.context_max_chars
        old = state.get("context", "") or ""
        rep = state.get("decision_report") or {}
        tools = state.get("tool_results", []) or []
        last_tool = tools[-1][:1200] if tools else ""
        intent = rep.get("intent", "") if isinstance(rep, dict) else ""
        addition = f"\n[turn intent={intent}] {last_tool[:800]}"
        new_ctx = (old + addition)[-cap:] if addition.strip() else old[-cap:]
        return {"context": new_ctx}
    except Exception as e:
        logger.error(f"context_refresh failed: {e}")
        return {}


def build_game_graph_v2(output_cache: OutputCache) -> StateGraph:
    """Re-imagined topology:
    START → classifier → worldgen → react_router ⇄ {search|image|redescribe} (≤3) → mechanics(fan-out)
      → context_refresh → story → pusher → END. Old builder untouched for compat.
    """
    logger.info("Building game graph v2 (react + atomic N4 + terminators)...")
    wf = StateGraph(GameState)
    wf.add_node("classifier", classifier_node)
    wf.add_node("worldgen", node0_worldgen)
    wf.add_node("react_router", react_router_node)
    wf.add_node("search", node1_web_search)
    wf.add_node("image", node2_image_processor)
    wf.add_node("redescribe", node3_redescriptor)
    wf.add_node("mechanics", node4_parallel)
    wf.add_node("context_refresh", context_refresh_node)
    wf.add_node("summarizer", node5_context_injector)

    async def story_wrap(s: GameState) -> Dict[str, Any]:
        # Inject rolling context into prompt-visible summary for N6 compat
        try:
            ctx = s.get("context", "") or ""
            if ctx and not s.get("context_summary"):
                return await node6_story_generator({**s, "rag_context": f"{s.get('rag_context','')}\n[rolling context]\n{ctx[-2000:]}"})
        except Exception:
            pass
        return await node6_story_generator(s)

    wf.add_node("story", story_wrap)

    async def pusher_wrap(s: GameState) -> Dict[str, Any]:
        return await node7_output_pusher(s, output_cache)

    wf.add_node("pusher", pusher_wrap)

    wf.add_edge(START, "classifier")
    wf.add_edge("classifier", "worldgen")
    wf.add_edge("worldgen", "react_router")
    wf.add_conditional_edges(
        "react_router", route_react,
        {"search": "search", "image": "image", "redescribe": "redescribe",
         "mechanics": "mechanics", "story": "story"},
    )
    # Re-entrant tools → back to router (multi-node capable: image+search)
    for t in ("search", "image", "redescribe"):
        wf.add_conditional_edges(
            t,
            lambda s: "react_router"
            if _budget_exhausted(s) is None and (
                s.get("needs_search") or s.get("needs_image_processing") or s.get("needs_re_description")
            ) else ("story" if _budget_exhausted(s) else "mechanics"),
            {"react_router": "react_router", "mechanics": "mechanics", "story": "story"},
        )
    wf.add_edge("mechanics", "context_refresh")
    wf.add_edge("context_refresh", "summarizer")
    wf.add_edge("summarizer", "story")
    wf.add_edge("story", "pusher")
    wf.add_edge("pusher", END)
    logger.info("Game graph v2 built")
    return wf
