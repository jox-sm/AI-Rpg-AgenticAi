from __future__ import annotations

import json

from langchain_core.tools import tool


@tool
async def use_skill(
    skill_name: str,
    current_stats_json: str = "{}",
    current_skills_json: str = "[]",
    target_json: str = "{}",
    modifier: int = 0,
    damage_multiplier: float = 1.0,
    mana: int = 50,
    max_mana: int = 100,
) -> str:
    """Execute a named skill with current character state and target context.
    Routes to the correct skill handler automatically.

    Args:
        skill_name: Name of the skill to use (e.g., 'slash', 'block', 'persuasion', 'fire_magic')
        current_stats_json: JSON string of current CharacterStats
        current_skills_json: JSON string of current skills list
        target_json: JSON string describing the target (enemy/item/NPC with type, defense, level, etc.)
        modifier: Flat modifier to the skill check roll
        damage_multiplier: Damage multiplier from plan quality, positioning, etc.
        mana: Current mana available
        max_mana: Maximum mana pool
    """
    from ....skills import SKILL_REGISTRY, get_skill, list_skills

    skill = get_skill(skill_name)
    if not skill:
        available = list_skills()
        return json.dumps({
            "error": f"Unknown skill: '{skill_name}'",
            "available_skills": available,
        }, indent=2)

    try:
        stats = json.loads(current_stats_json) if isinstance(current_stats_json, str) else current_stats_json
    except (json.JSONDecodeError, TypeError):
        stats = {}

    try:
        skills_data = json.loads(current_skills_json) if isinstance(current_skills_json, str) else current_skills_json
    except (json.JSONDecodeError, TypeError):
        skills_data = []

    try:
        target = json.loads(target_json) if isinstance(target_json, str) else target_json
    except (json.JSONDecodeError, TypeError):
        target = {}

    skill_level = 1
    for s in skills_data:
        if isinstance(s, dict):
            name = s.get("name", s.get("skill_name", "")).lower()
        else:
            name = str(s).lower()
        if name == skill_name.lower():
            skill_level = float(s.get("level", s.get("value", 1)))
            break

    handler = skill["handler"]
    stat_bonus = stats.get("level", 1) // 4 + stats.get("strength", 10) // 4

    ctx = {
        "skill_level": skill_level,
        "stat_bonus": stat_bonus,
        "modifier": modifier,
        "damage_multiplier": damage_multiplier,
        "target": target,
        "mana": mana,
        "max_mana": max_mana,
    }

    result = handler(ctx)
    result["skill_name"] = skill_name
    result["skill_category"] = skill.get("category", "")
    result["skill_level"] = skill_level

    return json.dumps(result, indent=2)
