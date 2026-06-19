from __future__ import annotations

import random

from .base import make_result, success_check, xp_gain


def _tactics(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    enemy_level = target.get("level", 5)
    diff = max(5, enemy_level * 2)
    check = success_check(lvl, diff, stat, 0)

    advantage = 0
    if check["success"]:
        advantage = 1 + int(lvl * 0.3)
        if check["quality"] == "critical":
            advantage *= 2

    xp = xp_gain(lvl, enemy_level / 5, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"You spot a tactical opening — next attack gains +{advantage} advantage" if advantage > 0 else "You see no tactical opportunity",
        skill_xp=xp, cooldown=1,
        attributes={"advantage_bonus": advantage},
    )


def _strategy_skill(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    plan_complexity = ctx.get("complexity", 1)

    diff = 5 + plan_complexity * 5
    check = success_check(lvl, diff, stat, 0)

    outcome = ""
    bonus = 0
    if check["success"]:
        bonus = 1 + int(lvl * 0.5)
        if check["quality"] == "critical":
            bonus = int(bonus * 1.5)
        outcomes = ["flanking route found", "enemy formation is weak", "escape route secured", "high ground identified", "reinforcements intercepted"]
        outcome = random.choice(outcomes)

    xp = xp_gain(lvl, plan_complexity, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Strategic insight: {outcome} (allies gain +{bonus} bonus)" if outcome else "Your plan has no clear advantage",
        skill_xp=xp, cooldown=2,
        attributes={"strategy_bonus": bonus, "insight": outcome},
    )


def _leadership(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    allies = ctx.get("ally_count", 1)

    diff = 5 + allies * 3
    check = success_check(lvl, diff, stat, 0)

    morale = 0
    if check["success"]:
        morale = int(lvl * 1.5 + stat)
        if check["quality"] == "critical":
            morale = int(morale * 1.5)

    xp = xp_gain(lvl, allies * 0.3, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Your leadership inspires {allies} allies (morale +{morale})" if morale > 0 else "Your words fail to inspire",
        skill_xp=xp, cooldown=2,
        attributes={"morale_boost": morale, "allies_affected": allies},
    )


def _planning(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    prep_time = ctx.get("prep_time", 1)

    diff = max(3, 10 - prep_time)
    check = success_check(lvl, diff, stat, 0)

    contingencies = 0
    if check["success"]:
        contingencies = 1 + int(lvl * 0.2)
        if check["quality"] == "critical":
            contingencies += 2

    xp = xp_gain(lvl, 0.5, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Your plan has {contingencies} backup plans" if contingencies > 0 else "Your plan is too rigid",
        skill_xp=xp, cooldown=1,
        attributes={"contingencies": contingencies},
    )


SKILLS: dict[str, dict] = {
    "tactics": {"handler": _tactics, "category": "strategy", "description": "Analyze combat situations for tactical advantages"},
    "strategy": {"handler": _strategy_skill, "category": "strategy", "description": "Develop battle plans and strategic approaches"},
    "leadership": {"handler": _leadership, "category": "strategy", "description": "Inspire and coordinate allies in combat"},
    "planning": {"handler": _planning, "category": "strategy", "description": "Prepare contingencies and think ahead"},
}
