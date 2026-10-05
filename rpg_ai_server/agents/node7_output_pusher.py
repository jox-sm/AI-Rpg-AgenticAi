from __future__ import annotations

from typing import Any, Dict

from ..schemas.state import GameState
from ..schemas.types import GameOutput
from ..redis.output_cache import OutputCache
from ..utils.coerce import as_dict, model_list
from ..utils.logger import logger


async def node7_output_pusher(state: GameState, output_cache: OutputCache) -> Dict[str, Any]:
    logger.info(f"[Node 7] Pushing output for UUID {state['uuid']}")

    try:
        output = GameOutput(
            uuid=state["uuid"],
            game_data={
                **state.get("game_data", {}),
                # Turn 1 carries models; turn 2+ carries plain Redis dicts.
                "character_stats": as_dict(state.get("character_stats")),
                "inventory": model_list(state.get("inventory")),
                "skills": model_list(state.get("skills")),
                "relationships": model_list(state.get("relationships")),
                "grid_data": {k: model_list(v) for k, v in state.get("grid_data", {}).items()},
            },
            story=state.get("story_output", ""),
            context_summary=as_dict(state.get("context_summary")) or {},
            tool_results=list(state.get("tool_results", []) or [])[-3:],
            # Death contract: final state is already saved by the orchestrator;
            # the frontend closes the game when this is True (or equivalently
            # game_data.character_stats.is_dead / game_data.player_dead).
            game_over=bool((state.get("game_data", {}) or {}).get("player_dead", False)),
        )

        success = await output_cache.store_result(output)

        if success:
            logger.info(f"Successfully pushed result for UUID {state['uuid']}")
        else:
            logger.error(f"Failed to push result for UUID {state['uuid']}")

        return {"game_output": output.model_dump(), "processed": True}

    except Exception as e:
        logger.error(f"Output push failed for UUID {state['uuid']}: {e}")
        return {"error": str(e), "processed": False}
