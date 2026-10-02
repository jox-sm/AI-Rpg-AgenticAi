from __future__ import annotations

import json
import math

from langchain_core.tools import tool

from ....schemas.enums import DiceType
from ....schemas.types import DiceRoll
from .common import DICE_MAP, MONSTER_DIFFICULTY, PLAN_QUALITY_BONUSES


@tool
async def situational_dice(
    player_level: int,
    plan_quality: str = "average",
    enemy_name: str = "",
    enemy_level: int = 0,
) -> str:
    """Analyze combat situation and recommend optimal dice configuration.
    Evaluates player power vs enemy difficulty plus plan/strategy quality,
    then returns recommended dice type, advantage/disadvantage, and modifier.

    Args:
        player_level: Current character level (required)
        plan_quality: How good the player's described action is:
            'none'/'reckless' - attacking with no plan, making things worse (-4 penalty)
            'poor' - bad approach that hinders success (-2 penalty)
            'average' - standard attack, nothing special (no modifier)
            'good' - decent tactical thinking (+2 bonus)
            'excellent' - smart plan exploiting enemy weaknesses (+4 bonus)
            'genius' - brilliant trap or masterful strategy (+6 bonus)
        enemy_name: Name of enemy to look up in bestiary
        enemy_level: Enemy level if not in bestiary (optional fallback)
    """
    enemy_lvl = enemy_level
    if enemy_name:
        monster_info = MONSTER_DIFFICULTY.get(enemy_name.strip().lower())
        if monster_info:
            enemy_lvl = monster_info["level"]

    if enemy_lvl <= 0:
        enemy_lvl = player_level

    power_ratio = player_level / max(enemy_lvl, 1)
    power_ratio = max(0.1, min(5.0, power_ratio))

    if power_ratio >= 2.0:
        power_bonus = 5
        power_desc = "overwhelming advantage"
    elif power_ratio >= 1.5:
        power_bonus = 3
        power_desc = "clear advantage"
    elif power_ratio >= 1.1:
        power_bonus = 1
        power_desc = "slight advantage"
    elif power_ratio >= 0.9:
        power_bonus = 0
        power_desc = "even match"
    elif power_ratio >= 0.6:
        power_bonus = -2
        power_desc = "slight disadvantage"
    elif power_ratio >= 0.4:
        power_bonus = -4
        power_desc = "clear disadvantage"
    else:
        power_bonus = -6
        power_desc = "overwhelming disadvantage"

    plan_info = PLAN_QUALITY_BONUSES.get(plan_quality.strip().lower(), PLAN_QUALITY_BONUSES["average"])
    plan_bonus = plan_info["advantage_bonus"]
    damage_mult = plan_info["damage_mult"]
    plan_desc = plan_info["desc"]

    total_modifier = power_bonus + plan_bonus

    recommend_advantage = False
    recommend_disadvantage = False
    if total_modifier >= 3:
        recommend_advantage = True
    elif total_modifier <= -3:
        recommend_disadvantage = True

    effective_bonus = total_modifier
    if recommend_advantage:
        effective_bonus = max(0, total_modifier - 3)
    elif recommend_disadvantage:
        effective_bonus = min(0, total_modifier + 3)

    return json.dumps({
        "analysis": f"Player lvl {player_level} vs enemy lvl {enemy_lvl} ({power_desc}). Plan: {plan_desc}.",
        "power_ratio": round(power_ratio, 2),
        "power_bonus": power_bonus,
        "power_description": power_desc,
        "plan_quality": plan_quality,
        "plan_bonus": plan_bonus,
        "plan_damage_multiplier": damage_mult,
        "total_situation_modifier": total_modifier,
        "recommended_dice": "d20",
        "recommended_advantage": recommend_advantage,
        "recommended_disadvantage": recommend_disadvantage,
        "recommended_modifier": effective_bonus,
        "recommended_damage_multiplier": damage_mult,
        "guidance": (
            "Use the recommended dice parameters in your dice_roller call. "
            f"Set modifier={effective_bonus}, advantage={recommend_advantage}, disadvantage={recommend_disadvantage}. "
            f"Apply damage_multiplier of {damage_mult}x to final damage via damage_multiplier tool."
        ),
    }, indent=2)


@tool
async def dice_roller(
    dice: str = "d20",
    count: int = 1,
    advantage: bool = False,
    disadvantage: bool = False,
    modifier: int = 0,
    reason: str = "",
) -> str:
    """Roll D&D dice with optional advantage/disadvantage.

    Args:
        dice: Dice type: d4, d6, d8, d10, d12, d20, d100
        count: Number of dice to roll (1-100)
        advantage: Roll twice, take higher (only for single die)
        disadvantage: Roll twice, take lower (only for single die)
        modifier: Flat modifier to add to total
        reason: Why this roll is being made
    """
    try:
        dice_type = DiceType(dice.lower())
    except ValueError:
        return json.dumps({"error": f"Invalid dice type: {dice}"})

    if not 1 <= count <= 100:
        raise ValueError("count must be between 1 and 100")

    from ....scripts.dice_engine import Dice as SCDice, roll as sc_roll

    sides = DICE_MAP[dice_type]
    results = []

    if advantage or disadvantage:
        for _ in range(count):
            pair = sc_roll(sides, 2)
            results.append(max(pair) if advantage else min(pair))
    else:
        results = sc_roll(sides, count)

    total = sum(results) + modifier
    roll = DiceRoll(
        dice=dice_type,
        count=count,
        advantage=advantage,
        disadvantage=disadvantage,
        modifier=modifier,
        results=results,
        total=total,
        reason=reason,
    )
    return json.dumps(roll.model_dump(), indent=2)
