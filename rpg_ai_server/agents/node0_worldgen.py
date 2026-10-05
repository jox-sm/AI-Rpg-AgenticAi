from __future__ import annotations

import copy
from typing import Any, Dict

from ..schemas.state import GameState
from ..scripts.world_generator import (
    ensure_world,
    grid_to_grid_data,
    maybe_expand_world,
    move_player,
    parse_move,
)
from ..utils.logger import logger


def _seed_for(state: GameState, game_data: Dict[str, Any]) -> str:
    world = game_data.get("world") or {}
    return str(
        game_data.get("world_seed")
        or (world.get("seed") if isinstance(world, dict) else None)
        or state.get("uuid")
        or "world"
    )


async def node0_worldgen(state: GameState) -> Dict[str, Any]:
    """Deterministic living-world pass: ensure grid, apply movement, expand at borders.

    Pure function of (seed, coords): no LLM, no Redis, no HTTP. Runs every turn
    right after the classifier so mechanics/story always see a fresh, bounded
    2D window while far cells regenerate identically on revisit. Also ages the
    adaptive-difficulty clock (turns/days survived).
    """
    try:
        game_data: Dict[str, Any] = copy.deepcopy(state.get("game_data") or {})
    except Exception:
        game_data = {}
    try:
        from ..scripts.xp_loot import advance_day_tracker
        seed = _seed_for(state, game_data)
        ensure_world(game_data, seed)
        advance_day_tracker(game_data)

        lines: list[str] = []
        mv = parse_move(state.get("prompt", ""))
        if mv is not None:
            dx, dy = mv
            info = move_player(game_data, dx, dy, world_seed=seed)
            to = info.get("moved_to", [])
            biome = info.get("biome", "Unknown")
            lines.append(f"- world: moved to ({to[0]},{to[1]}) — {biome}")
            exp = info.get("expansion") or {}
            if exp.get("expanded"):
                size = exp.get("new_size", [])
                lines.append(f"- world: expanded {','.join(exp['directions'])} to {size[0]}x{size[1]}")
            elif exp.get("blocked"):
                lines.append("- world: blocked (edge of known lands)")
        else:
            exp = maybe_expand_world(game_data)
            if exp.get("expanded"):
                size = exp.get("new_size", [])
                lines.append(f"- world: expanded {','.join(exp['directions'])} to {size[0]}x{size[1]}")
            elif exp.get("blocked"):
                lines.append("- world: blocked (edge of known lands)")

        try:
            grid_data = grid_to_grid_data(game_data.get("grid") or [], game_data.get("origin"))
        except Exception:
            grid_data = state.get("grid_data") or {}

        out: Dict[str, Any] = {"game_data": game_data, "grid_data": grid_data}
        if lines:
            out["tool_results"] = lines
        return out
    except Exception as e:
        logger.error(f"node0_worldgen failed: {e}")
        return {}
