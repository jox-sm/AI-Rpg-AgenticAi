from __future__ import annotations

import random

from .base import make_result, success_check, xp_gain


def _athletics(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    task_difficulty = ctx.get("difficulty", 10)

    diff = max(3, task_difficulty)
    check = success_check(lvl, diff, stat, 0, mastery_key="physical")

    xp = xp_gain(lvl, task_difficulty / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="You power through the physical challenge" if check["success"] else "Your strength fails you",
        skill_xp=xp, cooldown=0,
        attributes={"difficulty": task_difficulty},
    )


def _acrobatics(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    maneuver_difficulty = ctx.get("difficulty", 10)

    diff = max(3, maneuver_difficulty)
    check = success_check(lvl, diff, stat, 0, mastery_key="physical")

    xp = xp_gain(lvl, maneuver_difficulty / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="You flip, twist, and land gracefully" if check["success"] else "You stumble and fall",
        skill_xp=xp, cooldown=0,
        attributes={"difficulty": maneuver_difficulty},
    )


def _endurance(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    duration = ctx.get("duration", 1)

    diff = 5 + duration * 3
    check = success_check(lvl, diff, stat, 0, mastery_key="physical")

    stamina_gain = 0
    if check["success"]:
        stamina_gain = int(duration * (1 + lvl * 0.2))
        if check["quality"] == "critical":
            stamina_gain = int(stamina_gain * 1.5)

    xp = xp_gain(lvl, duration * 0.3, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"You endure — stamina +{stamina_gain}" if stamina_gain else "You collapse from exhaustion",
        skill_xp=xp, cooldown=1,
        attributes={"stamina_gain": stamina_gain},
    )


def _reflexes(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    trigger_speed = ctx.get("trigger_speed", 10)

    diff = max(3, trigger_speed)
    check = success_check(lvl, diff, stat, 0, mastery_key="physical")

    xp = xp_gain(lvl, trigger_speed / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="Lightning-fast reflexes kick in!" if check["success"] else "You react too slowly",
        skill_xp=xp, cooldown=0,
        attributes={"reaction_time": "instant" if check["success"] else "slow"},
    )


def _climbing(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    wall_difficulty = ctx.get("difficulty", 10)

    diff = max(3, wall_difficulty)
    check = success_check(lvl, diff, stat, 0, mastery_key="physical")

    fall_damage = 0
    if not check["success"]:
        fall_damage = random.randint(5, 15)

    xp = xp_gain(lvl, wall_difficulty / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="You scale the wall with ease" if check["success"] else f"You fall and take {fall_damage} damage!",
        damage=fall_damage, skill_xp=xp, cooldown=0,
        attributes={"difficulty": wall_difficulty, "fall_damage": fall_damage},
    )


SKILLS: dict[str, dict] = {
    "athletics": {"handler": _athletics, "category": "physical", "description": "Raw strength for lifting, pushing, breaking"},
    "acrobatics": {"handler": _acrobatics, "category": "physical", "description": "Balance, tumbling, and aerial maneuvers"},
    "endurance": {"handler": _endurance, "category": "physical", "description": "Push through fatigue and sustain effort"},
    "reflexes": {"handler": _reflexes, "category": "physical", "description": "Snap reactions to sudden events"},
    "climbing": {"handler": _climbing, "category": "physical", "description": "Scale walls, cliffs, and other vertical surfaces"},
}
