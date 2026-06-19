from __future__ import annotations

import random

from .base import make_result, success_check, xp_gain


def _smithing(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    item_rarity = ctx.get("item_rarity", 1)

    diff = 5 + item_rarity * 5
    check = success_check(lvl, diff, stat, 0)

    quality = "common"
    durability_bonus = 0
    if check["success"]:
        quality_roll = random.random() + lvl * 0.02
        if quality_roll > 1.5:
            quality = "masterwork"
        elif quality_roll > 1.0:
            quality = "fine"
        durability_bonus = int(lvl * 2)

    xp = xp_gain(lvl, item_rarity, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Forged a {quality} item (durability +{durability_bonus})" if check["success"] else "The metal cracks — smithing fails!",
        skill_xp=xp, cooldown=2,
        attributes={"quality": quality, "durability_bonus": durability_bonus, "rarity": item_rarity},
    )


def _alchemy(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    potion_tier = ctx.get("potion_tier", 1)

    diff = 5 + potion_tier * 6
    check = success_check(lvl, diff, stat, 0)

    potency = 1.0
    if check["success"]:
        potency = 1.0 + lvl * 0.03 + random.uniform(0, 0.2)
        if check["quality"] == "critical":
            potency *= 1.5

    xp = xp_gain(lvl, potion_tier, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Brewed a tier {potion_tier} potion (potency x{potency:.1f})" if check["success"] else "The mixture bubbles and spoils!",
        skill_xp=xp, cooldown=2,
        attributes={"potency": round(potency, 2), "tier": potion_tier},
    )


def _woodworking(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    project_complexity = ctx.get("complexity", 1)

    diff = 5 + project_complexity * 4
    check = success_check(lvl, diff, stat, 0)

    xp = xp_gain(lvl, project_complexity, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="Crafted a sturdy wooden item" if check["success"] else "The wood splinters and breaks",
        skill_xp=xp, cooldown=1,
        attributes={"complexity": project_complexity},
    )


def _enchanting(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    enchant_power = ctx.get("enchant_power", 1)
    mana = ctx.get("mana", 50)
    mana_cost = 15 * enchant_power

    if mana < mana_cost:
        return make_result(False, f"Not enough mana for enchanting ({mana}/{mana_cost})")

    diff = 5 + enchant_power * 8
    check = success_check(lvl, diff, stat, 0)

    effect_power = 0
    if check["success"]:
        effect_power = enchant_power + int(lvl * 0.3)
        if check["quality"] == "critical":
            effect_power = int(effect_power * 1.5)

    xp = xp_gain(lvl, enchant_power, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Item enchanted (power {effect_power}, mana -{mana_cost})" if check["success"] else "Enchantment collapses!",
        skill_xp=xp, cooldown=3,
        attributes={"enchant_power": effect_power, "mana_cost": mana_cost},
    )


SKILLS: dict[str, dict] = {
    "smithing": {"handler": _smithing, "category": "crafting", "description": "Forge and repair metal weapons and armor"},
    "alchemy": {"handler": _alchemy, "category": "crafting", "description": "Brew potions and concoctions"},
    "woodworking": {"handler": _woodworking, "category": "crafting", "description": "Craft wood-based items and structures"},
    "enchanting": {"handler": _enchanting, "category": "crafting", "description": "Infuse items with magical properties"},
}
