from __future__ import annotations

import random

from .base import damage_formula, make_result, success_check, xp_gain


def _spellcasting(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)
    mult = ctx.get("damage_multiplier", 1.0)
    mana = ctx.get("mana", 50)
    mana_cost = max(5, 10 - int(lvl * 0.5))

    if mana < mana_cost:
        return make_result(False, f"Not enough mana ({mana}/{mana_cost})")

    diff = max(5, target.get("magic_defense", 10))
    check = success_check(lvl, diff, stat, mod, mastery_key="magic")

    dmg = 0
    if check["success"]:
        dmg = damage_formula(10, lvl * 1.2, stat, mult)
        if check["quality"] == "critical":
            dmg = int(dmg * 1.5)

    xp = xp_gain(lvl, 1.2, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Spell strikes for {dmg} force damage (mana: -{mana_cost})" if check["success"] else "Spell fizzles!",
        damage=dmg, damage_type="force", skill_xp=xp, cooldown=0,
        attributes={"mana_cost": mana_cost},
    )


def _mana_control(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    mana = ctx.get("mana", 50)
    max_mana = ctx.get("max_mana", 100)

    recovered = int(5 + lvl * 2 + random.randint(1, 6))
    recovered = min(recovered, max_mana - mana)
    overflow = mana + recovered - max_mana

    xp = xp_gain(lvl, 0.5, True, "success")
    return make_result(
        success=True,
        effect=f"Mana control recovers {recovered} mana" + (f" ({overflow} overflow)" if overflow > 0 else ""),
        skill_xp=xp, cooldown=2,
        attributes={"mana_recovered": recovered},
    )


def _fire_magic(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mult = ctx.get("damage_multiplier", 1.0)
    mana = ctx.get("mana", 50)
    mana_cost = max(8, 15 - int(lvl * 0.5))

    if mana < mana_cost:
        return make_result(False, f"Not enough mana ({mana}/{mana_cost})")

    diff = max(5, target.get("magic_defense", 10) - 3)
    check = success_check(lvl, diff, stat, 0, mastery_key="magic")

    dmg = 0
    burn = False
    if check["success"]:
        dmg = damage_formula(12, lvl * 1.3, stat, mult)
        if random.random() < 0.4:
            burn = True
        if check["quality"] == "critical":
            dmg = int(dmg * 1.5)
            burn = True

    xp = xp_gain(lvl, 1.3, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Fireball hits for {dmg} fire damage" + (" (burns target!)" if burn else "") if check["success"] else "Fire spell fizzles!",
        damage=dmg, damage_type="fire", skill_xp=xp, cooldown=1,
        status_effects=["burn"] if burn else [],
        attributes={"mana_cost": mana_cost},
    )


def _ice_magic(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mult = ctx.get("damage_multiplier", 1.0)
    mana = ctx.get("mana", 50)
    mana_cost = max(8, 15 - int(lvl * 0.5))

    if mana < mana_cost:
        return make_result(False, f"Not enough mana ({mana}/{mana_cost})")

    diff = max(5, target.get("magic_defense", 10))
    check = success_check(lvl, diff, stat, 0, mastery_key="magic")

    dmg = 0
    freeze = False
    if check["success"]:
        dmg = damage_formula(10, lvl * 1.2, stat, mult)
        if check["quality"] in ("good", "critical"):
            freeze = True

    xp = xp_gain(lvl, 1.3, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Ice shard hits for {dmg} cold damage" + (" (freezes target!)" if freeze else "") if check["success"] else "Ice spell fizzles!",
        damage=dmg, damage_type="cold", skill_xp=xp, cooldown=1,
        status_effects=["freeze"] if freeze else [],
        attributes={"mana_cost": mana_cost},
    )


def _lightning_magic(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    targets = ctx.get("targets", [ctx.get("target", {})])
    stat = ctx.get("stat_bonus", 0)
    mult = ctx.get("damage_multiplier", 1.0)
    mana = ctx.get("mana", 50)
    mana_cost = max(10, 18 - int(lvl * 0.5))

    if mana < mana_cost:
        return make_result(False, f"Not enough mana ({mana}/{mana_cost})")

    hits = 0
    total_dmg = 0
    stunned = []
    for t in targets:
        if success_check(lvl, max(5, t.get("magic_defense", 10)), stat, 0, mastery_key="magic")["success"]:
            td = damage_formula(8, lvl, stat, mult * 0.8)
            total_dmg += td
            hits += 1
            if random.random() < 0.3:
                stunned.append(t.get("name", f"target_{hits}"))

    xp = xp_gain(lvl, 1.4, hits > 0, "good" if hits > 1 else "success")
    return make_result(
        success=hits > 0,
        effect=f"Chain lightning arcs to {hits} targets for {total_dmg} total lightning damage" + (f", stunning: {', '.join(stunned)}" if stunned else ""),
        damage=total_dmg, damage_type="lightning", skill_xp=xp, cooldown=2,
        status_effects=["stun"] * len(stunned),
        attributes={"targets_hit": hits, "mana_cost": mana_cost, "stunned": stunned},
    )


SKILLS: dict[str, dict] = {
    "spellcasting": {"handler": _spellcasting, "category": "magic", "description": "General spellcasting — versatile force damage"},
    "mana_control": {"handler": _mana_control, "category": "magic", "description": "Regenerate mana through focus and control"},
    "fire_magic": {"handler": _fire_magic, "category": "magic", "description": "Offensive fire spells with burn chance"},
    "ice_magic": {"handler": _ice_magic, "category": "magic", "description": "Cold spells that can freeze enemies"},  # intentional typo to match consistent naming pattern
    "lightning_magic": {"handler": _lightning_magic, "category": "magic", "description": "Chain lightning that arcs between enemies"},
}
