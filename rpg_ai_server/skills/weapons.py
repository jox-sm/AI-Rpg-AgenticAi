from __future__ import annotations

from .base import damage_formula, make_result, success_check, xp_gain


def _sword_mastery(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)
    mult = ctx.get("damage_multiplier", 1.0)

    diff = max(5, target.get("defense", 10) - int(lvl * 0.3))
    check = success_check(lvl, diff, stat, mod)

    dmg = 0
    if check["success"]:
        dmg = damage_formula(10, lvl * 1.2, stat, mult)
        if check["quality"] == "critical":
            dmg = int(dmg * 1.8)

    xp = xp_gain(lvl, 1.2, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Sword mastery strikes for {dmg} slashing damage (mastery bonus: {int(lvl*0.3)} bypass)",
        damage=dmg, damage_type="slashing", skill_xp=xp, cooldown=0,
    )


def _spear_mastery(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)
    mult = ctx.get("damage_multiplier", 1.0)

    diff = max(5, target.get("defense", 10))
    check = success_check(lvl, diff, stat, mod + int(lvl * 0.2))

    dmg = 0
    pen = 0
    if check["success"]:
        dmg = damage_formula(9, lvl, stat, mult)
        pen = int(lvl * 0.8)
        if check["quality"] == "critical":
            dmg = int(dmg * 1.5)
            pen *= 2

    xp = xp_gain(lvl, 1.2, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Spear thrust for {dmg} piercing (ignores {pen} armor)",
        damage=dmg, damage_type="piercing", skill_xp=xp, cooldown=0,
        attributes={"armor_penetration": pen},
    )


def _hammer_mastery(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)
    mult = ctx.get("damage_multiplier", 1.0)

    diff = max(5, target.get("defense", 10) + 3)
    check = success_check(lvl, diff, stat, mod)

    dmg = 0
    stun = False
    if check["success"]:
        dmg = damage_formula(14, lvl * 1.3, stat, mult)
        if check["quality"] in ("good", "critical"):
            stun = True

    xp = xp_gain(lvl, 1.3, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Hammer smash for {dmg} bludgeoning" + (" (stuns target!)" if stun else ""),
        damage=dmg, damage_type="bludgeoning",
        skill_xp=xp, cooldown=1,
        status_effects=["stun"] if stun else [],
    )


def _archery(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)
    mult = ctx.get("damage_multiplier", 1.0)

    diff = max(5, target.get("dodge", 5) + 5)
    check = success_check(lvl, diff, stat, mod)

    dmg = 0
    if check["success"]:
        dmg = damage_formula(8, lvl, stat, mult)
        if check["quality"] == "critical":
            dmg = int(dmg * 2.0)

    xp = xp_gain(lvl, 1.0, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Arrow {'hits' if check['success'] else 'misses'} for {dmg} piercing damage" + (" (critical shot!)" if check["quality"] == "critical" else ""),
        damage=dmg, damage_type="piercing", skill_xp=xp, cooldown=0,
        attributes={"ranged": True},
    )


def _dual_wield(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)
    mult = ctx.get("damage_multiplier", 1.0)

    diff = max(5, target.get("defense", 10))
    check1 = success_check(lvl, diff, stat, mod - 2)
    check2 = success_check(lvl, diff, stat, mod - 2)

    dmg = 0
    hits = 0
    if check1["success"]:
        dmg += damage_formula(6, lvl, stat, mult * 0.6)
        hits += 1
    if check2["success"]:
        dmg += damage_formula(6, lvl, stat, mult * 0.6)
        hits += 1

    xp = xp_gain(lvl, 1.3, hits > 0, "good" if hits == 2 else "success")
    return make_result(
        success=hits > 0,
        effect=f"Dual wield hits {hits} times for {dmg} total slashing damage",
        damage=dmg, damage_type="slashing", skill_xp=xp, cooldown=1,
        attributes={"hits": hits},
    )


SKILLS: dict[str, dict] = {
    "sword_mastery": {"handler": _sword_mastery, "category": "weapons", "description": "Mastery with swords — bypasses some armor"},
    "spear_mastery": {"handler": _spear_mastery, "category": "weapons", "description": "Expert spear thrusting with high armor penetration"},
    "hammer_mastery": {"handler": _hammer_mastery, "category": "weapons", "description": "Devastating hammer strikes that can stun"},
    "archery": {"handler": _archery, "category": "weapons", "description": "Ranged accuracy with bows and crossbows"},
    "dual_wield": {"handler": _dual_wield, "category": "weapons", "description": "Fight with a weapon in each hand for multiple strikes"},
}
