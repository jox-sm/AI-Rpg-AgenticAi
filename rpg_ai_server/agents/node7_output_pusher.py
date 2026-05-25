from __future__ import annotations

from typing import Any, Dict

from ..schemas.state import GameState
from ..schemas.types import GameOutput
from ..redis.output_cache import OutputCache
from ..utils.logger import logger


async def node7_output_pusher(state: GameState, output_cache: OutputCache) -> Dict[str, Any]:
    logger.info(f"[Node 7] Pushing output for UUID {state['uuid']}")

    try:
        output = GameOutput(
            uuid=state["uuid"],
            game_data={
                **state.get("game_data", {}),
                "character_stats": state.get("character_stats").model_dump() if state.get("character_stats") else None,
                "inventory": [i.model_dump() if hasattr(i, 'model_dump') else i for i in state.get("inventory", [])],
                "skills": [s.model_dump() if hasattr(s, 'model_dump') else s for s in state.get("skills", [])],
                "relationships": [r.model_dump() if hasattr(r, 'model_dump') else r for r in state.get("relationships", [])],
                "grid_data": {
                    k: [c.model_dump() if hasattr(c, 'model_dump') else c for c in v]
                    for k, v in state.get("grid_data", {}).items()
                },
            },
            story=state.get("story_output", ""),
            context_summary=state.get("context_summary").model_dump() if state.get("context_summary") else {},
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
