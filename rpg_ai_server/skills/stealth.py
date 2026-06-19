from __future__ import annotations

from .base import make_result, success_check, xp_gain


def _stealth(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)

    diff = max(5, target.get("perception", 10))
    check = success_check(lvl, diff, stat, mod)

    xp = xp_gain(lvl, 1.0, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="You vanish into the shadows" if check["success"] else "They spot you!",
        skill_xp=xp, cooldown=0,
        attributes={"hidden": check["success"], "margin": check["margin"]},
    )


def _sleight_of_hand(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)

    diff = max(5, target.get("perception", 10) + 5)
    check = success_check(lvl, diff, stat, mod)

    xp = xp_gain(lvl, 1.1, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="Your nimble fingers snatch it unnoticed" if check["success"] else "They catch your hand!",
        skill_xp=xp, cooldown=0,
    )


def _lockpick(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    difficulty = target.get("lock_difficulty", 10)
    diff = max(5, difficulty)
    check = success_check(lvl, diff, stat, 0)

    xp = xp_gain(lvl, difficulty / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="The lock clicks open" if check["success"] else "The lock holds — your picks bend",
        skill_xp=xp, cooldown=0,
        attributes={"lock_difficulty": difficulty},
    )


def _pickpocket(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    diff = max(8, target.get("perception", 10) + target.get("level", 5))
    check = success_check(lvl, diff, stat, 0)

    xp = xp_gain(lvl, 1.3, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="You lift their valuables without them noticing" if check["success"] else "They feel your hand and turn around!",
        skill_xp=xp, cooldown=1,
    )


SKILLS: dict[str, dict] = {
    "stealth": {"handler": _stealth, "category": "stealth", "description": "Move silently and hide in shadows"},
    "sleight_of_hand": {"handler": _sleight_of_hand, "category": "stealth", "description": "Quick hands for subtle manipulation"},
    "lockpick": {"handler": _lockpick, "category": "stealth", "description": "Open locks without the key"},
    "pickpocket": {"handler": _pickpocket, "category": "stealth", "description": "Steal from unaware targets"},
}
