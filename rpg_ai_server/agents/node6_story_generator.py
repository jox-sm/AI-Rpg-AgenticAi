from __future__ import annotations

import json
from typing import Any, Dict

from ..schemas.state import GameState
from ..utils.logger import logger
from ..utils.openrouter_client import get_openrouter_direct
from ..config.settings import settings


STORY_SYSTEM_PROMPT = """You are the D&D Storyteller, narrating an epic fantasy RPG adventure.

Your task is to take all game mechanics data and weave it into a compelling narrative response.

Input you will receive:
- Context summary (location, time, weather, quests, recent events)
- Grid/terrain analysis (what's in the environment)
- Tool results (dice rolls, damage calculations, stat changes, skill usage)
- Inventory updates
- Relationship status
- Search results (if any research was done)

Output rules:
1. Write in second person ("You see...", "You feel...")
2. Keep response under 500 words
3. Describe the environment vividly based on terrain/time data
4. Incorporate dice roll outcomes naturally
5. Mention skill usage and their effects
6. Reference inventory items when relevant
7. Set up clear narrative hooks for the next turn
8. Maintain consistency with established relationships and quests
9. Use proper D&D 5e flavor
10. Output as plain text narrative (not JSON)"""


STORY_USER_PROMPT_TEMPLATE = """Generate the next narrative beat for this D&D game session.

CONTEXT:
{context_summary}

ENVIRONMENT:
{grid_summary}

GAME MECHANICS:
{Tool Results}
{search_info}

INVENTORY:
{inventory_summary}

SKILLS:
{skills_summary}

CHARACTER:
Level {level} | HP: {hp}/{max_hp} | MP: {mp}/{max_mp}

RESPOND WITH THE NARRATIVE ONLY, NO OUT-OF-CHARACTER TEXT."""


async def node6_story_generator(state: GameState) -> Dict[str, Any]:
    logger.info(f"[Node 6] Story generation for UUID {state['uuid']}")

    client = get_openrouter_direct()

    try:
        ctx = state.get("context_summary")

        grid_summary = ""
        if state.get("grid_data"):
            terrain_summary = set()
            for cells in state["grid_data"].values():
                for cell in cells[:5]:
                    t = str(cell.terrain.value if hasattr(cell.terrain, 'value') else cell.terrain)
                    terrain_summary.add(t)
            grid_summary = f"Current biome: {', '.join(terrain_summary)}"

        if ctx:
            context_str = f"Location: {ctx.current_location}\nTime: {ctx.time_of_day}\nWeather: {ctx.weather}\nRecent: {'; '.join(ctx.recent_events[-3:])}\nNarrative: {ctx.narrative_context}"
        else:
            context_str = state.get("prompt", "No context available")

        tool_results = state.get("tool_results", [])
        tool_results_str = "\n".join(tool_results[-3:]) if tool_results else "No mechanics processed yet."

        search_info = f"\nLore Research: {state.get('search_results', 'N/A')[:300]}" if state.get("search_results") else ""

        inventory_items = state.get("inventory", [])
        inv_summary = "; ".join(f"{i.name}x{i.quantity}" for i in inventory_items[:10]) if inventory_items else "Standard equipment"

        skills_list = state.get("skills", [])
        skills_str = "; ".join(s.name for s in skills_list[:5]) if skills_list else "Basic skills"

        stats = state.get("character_stats")

        prompt = STORY_USER_PROMPT_TEMPLATE.format(
            context_summary=context_str,
            grid_summary=grid_summary,
            search_info=search_info,
            inventory_summary=inv_summary,
            skills_summary=skills_str,
            level=stats.level if stats else 1,
            hp=stats.health if stats else 100,
            max_hp=stats.max_health if stats else 100,
            mp=stats.mana if stats else 50,
            max_mp=stats.max_mana if stats else 50,
        ).replace("{Tool Results}", tool_results_str)

        result = await client.chat_completion(
            model=settings.models.story_model,
            messages=[
                {"role": "system", "content": STORY_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=8192,
        )

        story = result["choices"][0]["message"]["content"]

        return {
            "story_output": story,
            "processed": True,
        }

    except Exception as e:
        logger.error(f"Story generation failed: {e}")
        return {
            "story_output": f"The story continues... (generation error: {e})",
            "processed": True,
            "error": str(e),
        }
