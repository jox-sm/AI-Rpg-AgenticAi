"""Initial game-state construction + Redis model rehydration."""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from ...config.settings import settings
from ...schemas.state import GameState
from ...schemas.types import (
    CharacterStats, ChatMessage, ContextSummary, GameRequest, ImageData,
    InventoryItem, NodeDecision, Relationship, Skill,
)
from ...scripts.world_generator import ensure_world, grid_to_grid_data

def hydrate_models(initial_state: GameState) -> None:
    """Restore model objects after a Redis round-trip.

    ``character_stats``/``skills``/``inventory``/etc. are stored as JSON
    dict(-list)s; nodes downstream expect model objects again.
    """
    model_map = {
        "character_stats": CharacterStats,
        "context_summary": ContextSummary,
        "decision": NodeDecision,
    }
    for key, model in model_map.items():
        value = initial_state.get(key)
        if value is not None and isinstance(value, dict):
            try:
                initial_state[key] = model.model_validate(value)
            except Exception:
                pass

    for key, model in (
        ("skills", Skill),
        ("inventory", InventoryItem),
        ("relationships", Relationship),
        ("chat_log", ChatMessage),
    ):
        items = initial_state.get(key)
        if isinstance(items, list):
            hydrated = []
            for item in items:
                if isinstance(item, dict):
                    try:
                        hydrated.append(model.model_validate(item))
                        continue
                    except Exception:
                        pass
                hydrated.append(item)
            if hydrated != items:
                initial_state[key] = hydrated


def build_initial_state(request: GameRequest) -> GameState:
    import time as _time
    import uuid as _uuid
    stats = CharacterStats()

    # Deterministic infinite world: dense 2D window + origin + player_pos,
    # all inside game_data so it persists across turns. Client fields in
    # request.data are preserved; missing world keys are filled in.
    base_data = dict(request.data) if isinstance(request.data, dict) else {}
    # Seed precedence: an explicit client seed wins (the web derives it from
    # the catalog game id, so every session of the same game lands in the
    # same world); the session id keeps per-scenario worlds otherwise.
    ensure_world(base_data, base_data.get("world_seed") or request.uuid)
    grid_data = grid_to_grid_data(base_data.get("grid") or [], base_data.get("origin"))

    initial_state: GameState = {
        "uuid": request.uuid,
        "prompt": request.prompt,
        "input_data": request.data or {},
        "game_data": base_data,
        "images": {},
        "grid_data": grid_data,
        "re_description_data": None,
        "context_summary": None,
        "character_stats": stats,
        "skills": [
            Skill(
                name="Basic Attack",
                skill_type="attack",
                cooldown=0,
                max_cooldown=1,
                level=1,
                description="A basic melee or ranged attack",
            ),
            Skill(
                name="Dodge",
                skill_type="defense",
                cooldown=0,
                max_cooldown=2,
                level=1,
                description="Dodge incoming attack",
                is_passive=False,
            ),
        ],
        "inventory": [],
        "relationships": [],
        "story_output": "",
        "decision": None,
        "needs_search": False,
        "needs_image_processing": False,
        "needs_re_description": False,
        "processed": False,
        "error": None,
        "search_results": "",
        "rag_context": "",
        "tool_results": [],
        "game_output": None,
        "conditional_passes": 0,
        "remaining_steps": settings.app.loop_recursion_limit,
        "__next__": "mechanics",
        # Re-imagined generous-local additions
        "context": "",
        "chat_log": [{"role": "user", "text": request.prompt, "turn": 0}],
        "decision_report": None,
        "budget": {"llm_calls": 0, "tokens_est": 0, "started_at": _time.time()},
        "next_node": "mechanics",
        "router_trace": [],
        "force_exit_reason": None,
        "turn_id": f"{request.uuid}:{_uuid.uuid4().hex[:8]}",
    }

    if request.images:
        from uuid import uuid4
        from ...schemas.types import ImageData
        import time
        for img in request.images:
            img_uuid = str(uuid4())
            initial_state["images"][img_uuid] = ImageData(
                image_uuid=img_uuid,
                game_uuid=request.uuid,
                url=img.get("url", ""),
                format=img.get("format", "webp"),
                timestamp=time.time(),
            )
        initial_state["needs_image_processing"] = True

    return initial_state
