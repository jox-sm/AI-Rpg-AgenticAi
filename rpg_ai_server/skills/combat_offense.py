from __future__ import annotations

import random
from typing import Any

from .base import damage_formula, make_result, success_check, xp_gain


def _slash(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)
    mult = ctx.get("damage_multiplier", 1.0)

    diff = max(5, target.get("defense", 10) - 2)
    check = success_check(lvl, diff, stat, mod, mastery_key="combat_offense")

    dmg = 0
    status = []
    if check["success"]:
        dmg = damage_formula(8, lvl, stat, mult)
        if check["quality"] == "critical":
            dmg = int(dmg * 1.5)
            status.append("bleed")
        if random.random() < 0.2:
            status.append("bleed")

    xp = xp_gain(lvl, 1.0, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Slash {'hits' if check['success'] else 'misses'} for {dmg} slashing damage" + (f" ({check['quality']})" if check["success"] else ""),
        damage=dmg, damage_type="slashing", skill_xp=xp,
        cooldown=0, status_effects=status,
    )


def _pierce(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)
    mult = ctx.get("damage_multiplier", 1.0)

    diff = max(5, target.get("defense", 10))
    check = success_check(lvl, diff, stat, mod, mastery_key="combat_offense")

    dmg = 0
    armor_pen = 0
    if check["success"]:
        dmg = damage_formula(7, lvl, stat, mult)
        armor_pen = 3 + int(lvl * 0.5)
        if check["quality"] == "critical":
            dmg = int(dmg * 1.5)
            armor_pen *= 2

    xp = xp_gain(lvl, 1.0, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Pierce {'hits' if check['success'] else 'misses'} for {dmg} piercing damage (ignores {armor_pen} armor)",
        damage=dmg, damage_type="piercing", skill_xp=xp,
        cooldown=0,
        attributes={"armor_penetration": armor_pen},
    )


def _bludgeon(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)
    mult = ctx.get("damage_multiplier", 1.0)

    diff = max(5, target.get("defense", 10) + 2)
    check = success_check(lvl, diff, stat, mod, mastery_key="combat_offense")

    dmg = 0
    stun = False
    if check["success"]:
        dmg = damage_formula(10, lvl, stat, mult)
        if check["quality"] in ("good", "critical"):
            stun = True

    xp = xp_gain(lvl, 1.1, check["success"], check["quality"])
    status = ["stun"] if stun else []
    return make_result(
        success=check["success"],
        effect=f"Bludgeon {'hits' if check['success'] else 'misses'} for {dmg} bludgeoning damage" + (" (stuns!)" if stun else ""),
        damage=dmg, damage_type="bludgeoning", skill_xp=xp,
        cooldown=0, status_effects=status,
    )


def _power_attack(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)
    mult = ctx.get("damage_multiplier", 1.0)

    diff = max(5, target.get("defense", 10) + 5)
    check = success_check(lvl, diff, stat, mod - 3, mastery_key="combat_offense")

    dmg = 0
    if check["success"]:
        dmg = damage_formula(14, lvl, stat, mult * 1.5)
        if check["quality"] == "critical":
            dmg = int(dmg * 2.0)

    xp = xp_gain(lvl, 1.3, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Power attack {'hits' if check['success'] else 'misses'} for {dmg} damage (high risk, high reward)",
        damage=dmg, damage_type="bludgeoning", skill_xp=xp,
        cooldown=1,
    )


def _cleave(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    targets = ctx.get("targets", [ctx.get("target", {})])
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)
    mult = ctx.get("damage_multiplier", 1.0)

    dmg = 0
    hits = 0
    for t in targets:
        diff = max(5, t.get("defense", 10))
        check = success_check(lvl, diff, stat, mod - 2, mastery_key="combat_offense")
        if check["success"]:
            td = damage_formula(6, lvl, stat, mult * 0.7)
            dmg += td
            hits += 1

    xp = xp_gain(lvl, 1.2, hits > 0, "success" if hits > 0 else "failure")
    return make_result(
        success=hits > 0,
        effect=f"Cleave hits {hits} targets for {dmg} total slashing damage",
        damage=dmg, damage_type="slashing", skill_xp=xp,
        cooldown=2,
        attributes={"targets_hit": hits},
    )


SKILLS: dict[str, dict] = {
    "slash": {"handler": _slash, "category": "combat_offense", "description": "A wide slashing strike that can cause bleeding"},
    "pierce": {"handler": _pierce, "category": "combat_offense", "description": "A precise thrust that ignores armor"},
    "bludgeon": {"handler": _bludgeon, "category": "combat_offense", "description": "A heavy blunt strike that can stun"},
    "power_attack": {"handler": _power_attack, "category": "combat_offense", "description": "A devastating but inaccurate heavy strike"},
    "cleave": {"handler": _cleave, "category": "combat_offense", "description": "Swing through multiple adjacent enemies"},
}
