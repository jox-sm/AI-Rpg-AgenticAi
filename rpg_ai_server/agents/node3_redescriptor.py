from __future__ import annotations

import json
from typing import Any, Dict, List

from ..schemas.state import GameState
from ..schemas.types import GridCell, ReDescriptionData
from ..utils.logger import logger
from ..utils.openrouter_client import get_openrouter_direct
from ..config.settings import settings


REDESCRIPTION_SYSTEM_PROMPT = """You are a D&D world re-description engine. Given previous grid cell data and a time change,
regenerate entities, items, and descriptions to reflect the new time of day or narrative context.

Input format:
{
  "previous_grid": [array of grid cells with items, ores, entities, terrain, prerequisites, cell, description],
  "time_change": "what changed (e.g., 'day to night', 'weather shifted to storm')"
}

Output format: Return the SAME structure but with updated entities, descriptions, and any items that change with time.
- Entities MUST change based on time (night = nocturnal/undead, day = diurnal animals)
- Items are mostly static unless looted or placed
- Ores don't change
- Descriptions update to reflect new time/lighting conditions
- Keep the same 15x15 grid, 225 cells total
- Return valid JSON object with "0,0" through "14,14" keys"""


async def node3_redescriptor(state: GameState) -> Dict[str, Any]:
    logger.info(f"[Node 3] Re-description triggered for UUID {state['uuid']}")

    if not state.get("re_description_data"):
        logger.warning("No re-description data provided")
        return {"needs_re_description": False}

    re_data: ReDescriptionData = state["re_description_data"]
    client = get_openrouter_direct()

    try:
        previous_cells = []
        for cell in re_data.previous_grid_data:
            previous_cells.append(cell.model_dump() if hasattr(cell, 'model_dump') else cell)

        payload = {
            "previous_grid": previous_cells,
            "time_change": re_data.time_change or "narrative progression",
        }

        user_prompt = json.dumps(payload, indent=2)

        result = await client.chat_completion(
            model=settings.models.redescription_model,
            messages=[
                {"role": "system", "content": REDESCRIPTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=65536,
        )

        raw_content = result["choices"][0]["message"]["content"]
        parsed = json.loads(raw_content)

        updated_grid: Dict[str, List[GridCell]] = {}
        for image_uuid, cells_raw in state.get("grid_data", {}).items():
            new_cells = []
            for x in range(15):
                for y in range(15):
                    key = f"{x},{y}"
                    cell_raw = parsed.get(key, {})
                    cell = GridCell(
                        items=cell_raw.get("items", []),
                        ores=[o.lower() for o in cell_raw.get("ores", []) if o],
                        entities=cell_raw.get("entities", []),
                        terrain=cell_raw.get("terrain", "unknown"),
                        prerequisites=cell_raw.get("prerequisites", []),
                        cell=(x, y),
                        description=cell_raw.get("description", "")[:200],
                    )
                    new_cells.append(cell)
            updated_grid[image_uuid] = new_cells

        return {
            "grid_data": updated_grid,
            "needs_re_description": False,
        }

    except Exception as e:
        logger.error(f"Re-description failed: {e}")
        return {"needs_re_description": False, "error": str(e)}
