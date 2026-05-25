from __future__ import annotations

import json
from typing import Any, Dict, List

from ..schemas.state import GameState
from ..schemas.types import GridCell, ImageData, Terrain
from ..utils.logger import logger
from ..utils.openrouter_client import get_openrouter_direct
from ..config.settings import settings


GRID_SYSTEM_PROMPT = """You are a D&D world perception engine. Analyze the provided image as a 15x15 grid and output a JSON object where each key is a cell coordinate like "0,0" and the value follows this EXACT schema:

{
  "items": [{"name": "item_name", "category": "weapon/armour/tool/potion/food/material/key_item/currency/magic"}],
  "ores": ["iron/coal/gold/diamond/emerald/copper/silver/mithril/adamantite/runite or empty"],
  "entities": [{"name": "entity_name", "type": "monster/animal/npc/hostile/neutral/friendly/boss", "count": 1}],
  "terrain": "one_of: plains/forest/desert/mountains/swamp/ocean/river/cave/dungeon/graveyard/savanna/tundra/jungle/volcano/city/ruins",
  "prerequisites": ["what players need to traverse this cell biome"],
  "cell": [x, y],
  "description": "max 2 lines describing what's visible here"
}

Rules:
- Terrain determines entities: morning+savanna = lions/deer; night+graveyard = skeletons/zombies
- Items must be D&D-appropriate fantasy items
- Ores only appear in mountain/cave/dungeon/cave biomes
- Prerequisites relate to traversal (boat for ocean, climbing gear for mountains, torch for cave)
- Each cell description max 2 lines (200 chars)
- The full output must be valid parseable JSON with 225 entries (15x15)"""


def _create_cell_key(x: int, y: int) -> str:
    return f"{x},{y}"


def _generate_empty_grid() -> Dict[str, Any]:
    cells = {}
    for x in range(15):
        for y in range(15):
            key = _create_cell_key(x, y)
            cells[key] = {
                "items": [],
                "ores": [],
                "entities": [],
                "terrain": "unknown",
                "prerequisites": [],
                "cell": [x, y],
                "description": "",
            }
    return cells


async def node2_image_processor(state: GameState) -> Dict[str, Any]:
    logger.info(f"[Node 2] Image processing triggered for UUID {state['uuid']}")

    if not state.get("images"):
        logger.warning("No images to process")
        return {"needs_image_processing": False, "grid_data": {}}

    client = get_openrouter_direct()
    grid_data: Dict[str, List[GridCell]] = {}

    for image_uuid, image_data in state["images"].items():
        logger.info(f"Processing image {image_uuid}")
        try:
            image_content = json.dumps(image_data.model_dump() if hasattr(image_data, 'model_dump') else image_data, indent=2)
            user_prompt = f"Analyze this D&D game image frame and produce a 15x15 grid analysis:\n\n{image_content}\n\nReturn a complete 15x15 grid JSON (225 cells) with coordinates 0,0 through 14,14."

            result = await client.chat_completion(
                model=settings.models.image_model,
                messages=[
                    {"role": "system", "content": GRID_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=8192,
            )

            raw_content = result["choices"][0]["message"]["content"]
            parsed = json.loads(raw_content)

            cells: List[GridCell] = []
            for x in range(15):
                for y in range(15):
                    key = _create_cell_key(x, y)
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
                    cells.append(cell)

            grid_data[image_uuid] = cells
            image_data.grid = cells

        except Exception as e:
            logger.error(f"Failed to process image {image_uuid}: {e}")

    return {
        "grid_data": grid_data,
        "needs_image_processing": False,
    }
