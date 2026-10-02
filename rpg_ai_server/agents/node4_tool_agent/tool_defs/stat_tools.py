from __future__ import annotations

import json

from langchain_core.tools import tool

from ....schemas.types import CharacterStats, Skill
from .common import MONSTER_DIFFICULTY, STAT_CAP_TABLE


@tool
async def stats_multiplier_and_updater(
    current_stats_json: str,
    monster_name: str = "",
    exp_gained: int = 0,
    monster_difficulty: str = "medium",
    should_level_up: bool = False,
) -> str:
    """Track experience and monster difficulty, level up characters, and update stats.

    Args:
        current_stats_json: JSON string of current CharacterStats
        monster_name: Name of defeated monster
        exp_gained: Experience points gained (if known)
        monster_difficulty: Difficulty rating (easy, medium, hard, boss)
    """
    try:
        stats_dict = json.loads(current_stats_json)
    except (json.JSONDecodeError, TypeError):
        stats_dict = {}

    stats = CharacterStats(**stats_dict)

    if monster_name:
        monster_info = MONSTER_DIFFICULTY.get(monster_name.lower(), None)
        if monster_info:
            exp_gained = monster_info["exp"]
        else:
            difficulty_mult = {"easy": 30, "medium": 75, "hard": 200, "boss": 500}
            exp_gained = difficulty_mult.get(monster_difficulty.lower(), 75)

    stats.experience += exp_gained
    level_ups = 0
    while stats.experience >= stats.experience_to_next:
        stats.experience -= stats.experience_to_next
        stats.level += 1
        level_ups += 1
        stats.experience_to_next = int(stats.experience_to_next * 1.5)
        stats.stat_cap = STAT_CAP_TABLE.get(min(stats.level, 10), stats.stat_cap + 2)
        stats.attribute_points += 2
        stats.max_health += 10 + stats.level
        stats.max_mana += 5 + stats.level // 2

    stats.carry_capacity = stats.strength * 5
    if level_ups > 0 or should_level_up:
        stats.health = stats.max_health
        stats.mana = stats.max_mana
        stats.current_load = 0.0

    return json.dumps(stats.model_dump(), indent=2)


@tool
async def skill_updater_and_validator(
    current_skills_json: str,
    action: str = "check_cooldowns",
    skill_name: str = "",
    new_skill_json: str = "",
    sacrifice_skills: str = "",
) -> str:
    """Update skill cooldowns, validate skill usage, handle new skill acquisition.

    Args:
        current_skills_json: JSON string of current skills array
        action: Action to perform - 'check_cooldowns', 'reduce_cooldowns', 'use_skill', 'add_skill', 'sacrifice_for_new'
        skill_name: Name of the skill being used (for use_skill action)
        new_skill_json: JSON string of new skill to add (for add_skill action)
        sacrifice_skills: Comma-separated skill names to sacrifice (for sacrifice_for_new action)
    """
    try:
        skills_data = json.loads(current_skills_json) if isinstance(current_skills_json, str) else current_skills_json
    except (json.JSONDecodeError, TypeError):
        skills_data = []

    skills = [Skill(**s) if isinstance(s, dict) else s for s in skills_data]

    if action == "reduce_cooldowns":
        for skill in skills:
            if skill.cooldown > 0:
                skill.cooldown -= 1
        return json.dumps([s.model_dump() for s in skills], indent=2)

    elif action == "check_cooldowns":
        available = [s.name for s in skills if s.cooldown == 0 and not s.is_passive]
        on_cooldown = [{"name": s.name, "cooldown": s.cooldown} for s in skills if s.cooldown > 0]
        return json.dumps({"available": available, "on_cooldown": on_cooldown}, indent=2)

    elif action == "use_skill":
        for skill in skills:
            if skill.name == skill_name:
                if skill.cooldown > 0:
                    return json.dumps({"error": f"Skill '{skill_name}' on cooldown for {skill.cooldown} more turns"})
                skill.cooldown = skill.max_cooldown
                return json.dumps({"success": True, "skill": skill.model_dump()}, indent=2)
        return json.dumps({"error": f"Skill '{skill_name}' not found"}, indent=2)

    elif action == "add_skill":
        try:
            new_skill_data = json.loads(new_skill_json) if isinstance(new_skill_json, str) else new_skill_json
            new_skill = Skill(**new_skill_data) if isinstance(new_skill_data, dict) else new_skill_data
            skills.append(new_skill)
            return json.dumps([s.model_dump() for s in skills], indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to add skill: {e}"}, indent=2)

    elif action == "sacrifice_for_new":
        names_to_sacrifice = [n.strip() for n in sacrifice_skills.split(",")]
        sacrificed = [s for s in skills if s.name in names_to_sacrifice]
        if not sacrificed:
            return json.dumps({"error": "No matching skills to sacrifice"}, indent=2)

        avg_level = sum(s.level for s in sacrificed) / len(sacrificed)
        combined_type = max(set(s.skill_type.value for s in sacrificed), key=lambda t: sum(1 for sk in sacrificed if sk.skill_type.value == t))

        new_skill_name = f"Mastered {'+'.join(s.name for s in sacrificed)}"
        new_skill = Skill(
            name=new_skill_name,
            skill_type=combined_type,
            level=int(avg_level) + 1,
            max_cooldown=max(s.max_cooldown for s in sacrificed),
            description=f"Evolved from sacrificing: {sacrifice_skills}",
        )

        skills = [s for s in skills if s.name not in names_to_sacrifice]
        skills.append(new_skill)
        return json.dumps({"new_skill": new_skill.model_dump(), "remaining_skills": [s.model_dump() for s in skills]}, indent=2)

    return json.dumps({"error": f"Unknown action: {action}"}, indent=2)
