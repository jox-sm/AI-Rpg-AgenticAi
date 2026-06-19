from __future__ import annotations

import random

from .base import make_result, success_check, xp_gain


def _block(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    incoming = ctx.get("incoming_damage", 0)
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)

    diff = max(5, int(incoming * 0.5))
    check = success_check(lvl, diff, stat, mod)

    blocked = 0
    if check["success"]:
        blocked = int(incoming * (0.3 + lvl * 0.03))
        blocked = min(blocked, incoming)

    xp = xp_gain(lvl, incoming / 20, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Block reduces damage by {blocked} ({'full' if blocked >= incoming else 'partial'} block)",
        damage=0, skill_xp=xp, cooldown=0,
        attributes={"damage_blocked": blocked, "remaining": incoming - blocked},
    )


def _parry(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    incoming = ctx.get("incoming_damage", 0)
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)

    diff = max(8, int(incoming * 0.6))
    check = success_check(lvl, diff, stat, mod)

    riposte = False
    blocked = 0
    if check["success"]:
        blocked = incoming
        if check["quality"] in ("good", "critical"):
            riposte = True

    xp = xp_gain(lvl, 1.3, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Parry {'deflects' if check['success'] else 'fails to deflect'} the attack" + (" (riposte ready!)" if riposte else ""),
        damage=0, skill_xp=xp, cooldown=1,
        attributes={"damage_blocked": blocked, "riposte": riposte},
    )


def _dodge(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    incoming = ctx.get("incoming_damage", 0)
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)

    diff = max(6, int(incoming * 0.4))
    check = success_check(lvl, diff, stat, mod)

    xp = xp_gain(lvl, 1.1, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="Dodge evades the attack entirely!" if check["success"] else "Dodge fails!",
        damage=0 if check["success"] else incoming,
        skill_xp=xp, cooldown=0,
        attributes={"evaded": check["success"], "remaining_damage": 0 if check["success"] else incoming},
    )


def _shield_wall(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    incoming = ctx.get("incoming_damage", 0)
    stat = ctx.get("stat_bonus", 0)

    reduction = int(incoming * (0.4 + lvl * 0.02))
    reduction = min(reduction, incoming)
    remaining = incoming - reduction

    xp = xp_gain(lvl, 1.2, True, "success")
    return make_result(
        success=True,
        effect=f"Shield wall absorbs {reduction} damage, {remaining} gets through",
        damage=remaining, skill_xp=xp, cooldown=2,
        attributes={"damage_blocked": reduction, "remaining": remaining},
    )


SKILLS: dict[str, dict] = {
    "block": {"handler": _block, "category": "combat_defense", "description": "Raise your weapon or shield to block incoming damage"},
    "parry": {"handler": _parry, "category": "combat_defense", "description": "Deflect an attack and leave the attacker open to riposte"},
    "dodge": {"handler": _dodge, "category": "combat_defense", "description": "Dodge out of the way of an incoming attack"},
    "shield_wall": {"handler": _shield_wall, "category": "combat_defense", "description": "Brace behind your shield for heavy damage reduction"},
}
