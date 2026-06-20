from __future__ import annotations

import random

from ..utils.mastery import get_mastery_config, get_mastery_skills, mastery_check, mastery_table
from ..utils.worker_manager import (
    find_workers_at_location,
    format_worker_option,
    worker_skill_level,
    worker_mastery_check,
)
from .base import make_result, xp_gain

_RARITY_TO_DIFF = {1: "trivial", 2: "easy", 3: "normal", 4: "hard", 5: "very_hard", 6: "legendary"}


def _difficulty_label(val: int) -> str:
    return _RARITY_TO_DIFF.get(val, "normal")


_SKILL_TO_MASTERY = {
    "smithing": "smithing",
    "alchemy": "alchemy",
    "woodworking": "woodworking",
    "enchanting": "enchanting",
}


_SKILL_TO_STATION = {
    "smithing": "Forge",
    "alchemy": "Alchemy Lab",
    "woodworking": "Workbench",
    "enchanting": "Enchanting Table",
}


def check_worker_availability(
    skill_name: str,
    player_location: str,
    player_level: int,
) -> dict:
    mastery_key = _SKILL_TO_MASTERY.get(skill_name, skill_name)
    station = _SKILL_TO_STATION.get(skill_name, "")

    workers = find_workers_at_location(player_location)
    relevant = [w for w in workers if mastery_key in {k.lower().strip() for k in w.get("mastery", {})}]

    if not relevant:
        return {"workers_available": False, "workers": [], "station": station}

    options = [format_worker_option(w, mastery_key) for w in relevant]
    return {
        "workers_available": True,
        "workers": options,
        "station": station,
        "message": (
            f"Workers are available at this {station}! "
            f"Your {skill_name} mastery is Lv{player_level}. "
            "Hire a worker or do it yourself."
        ),
    }


def _run_player_craft(
    lvl: int,
    mastery_key: str,
    diff_label: str,
    stat: int,
) -> dict:
    return mastery_check(lvl, mastery_key, diff_label, stat)


def _run_worker_craft(
    worker_id: str,
    mastery_key: str,
    diff_label: str,
    stat: int,
) -> dict | None:
    return worker_mastery_check(worker_id, mastery_key, diff_label, stat)


def _smithing(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    item_rarity = ctx.get("item_rarity", 1)
    worker_id = ctx.get("worker_id")

    diff = _difficulty_label(item_rarity)

    if worker_id:
        check = _run_worker_craft(worker_id, "smithing", diff, stat)
        if check is None:
            return make_result(False, f"Worker {worker_id} not found or can't smith")
        lvl = check["skill_level"]
    else:
        check = _run_player_craft(lvl, "smithing", diff, stat)

    quality = "common"
    durability_bonus = 0
    if check["success"]:
        quality_roll = random.random() + lvl * 0.02
        if quality_roll > 1.5:
            quality = "masterwork"
        elif quality_roll > 1.0:
            quality = "fine"
        durability_bonus = int(lvl * 2)

    who = f"Worker (Lv{lvl})" if worker_id else f"Self (Lv{lvl})"
    rate_pct = round(check["effective_rate"] * 100, 1)
    xp = xp_gain(lvl, item_rarity, check["success"], check["quality"])
    attrs = {"quality": quality, "durability_bonus": durability_bonus, "rarity": item_rarity,
             "mastery_rate": rate_pct, "mastery_level": lvl, "mastery_skill": "smithing"}
    if worker_id:
        attrs["worker_id"] = worker_id
        attrs["crafted_by"] = "worker"
    else:
        attrs["crafted_by"] = "player"

    return make_result(
        success=check["success"],
        effect=f"[{who} — {rate_pct}%] Forged a {quality} item (durability +{durability_bonus})" if check["success"]
               else f"[{who} — {rate_pct}%] The metal cracks — smithing fails!",
        skill_xp=xp, cooldown=2,
        attributes=attrs,
    )


def _alchemy(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    potion_tier = ctx.get("potion_tier", 1)
    worker_id = ctx.get("worker_id")

    diff = _difficulty_label(potion_tier)

    if worker_id:
        check = _run_worker_craft(worker_id, "alchemy", diff, stat)
        if check is None:
            return make_result(False, f"Worker {worker_id} not found or can't brew")
        lvl = check["skill_level"]
    else:
        check = _run_player_craft(lvl, "alchemy", diff, stat)

    potency = 1.0
    if check["success"]:
        potency = 1.0 + lvl * 0.03 + random.uniform(0, 0.2)
        if check["quality"] == "critical":
            potency *= 1.5

    who = f"Worker (Lv{lvl})" if worker_id else f"Self (Lv{lvl})"
    rate_pct = round(check["effective_rate"] * 100, 1)
    xp = xp_gain(lvl, potion_tier, check["success"], check["quality"])
    attrs = {"potency": round(potency, 2), "tier": potion_tier,
             "mastery_rate": rate_pct, "mastery_level": lvl, "mastery_skill": "alchemy"}
    if worker_id:
        attrs["worker_id"] = worker_id
        attrs["crafted_by"] = "worker"
    else:
        attrs["crafted_by"] = "player"

    return make_result(
        success=check["success"],
        effect=f"[{who} — {rate_pct}%] Brewed a tier {potion_tier} potion (potency x{potency:.1f})" if check["success"]
               else f"[{who} — {rate_pct}%] The mixture bubbles and spoils!",
        skill_xp=xp, cooldown=2,
        attributes=attrs,
    )


def _woodworking(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    complexity = ctx.get("complexity", 1)
    worker_id = ctx.get("worker_id")

    diff = _difficulty_label(complexity)

    if worker_id:
        check = _run_worker_craft(worker_id, "woodworking", diff, stat)
        if check is None:
            return make_result(False, f"Worker {worker_id} not found or can't woodwork")
        lvl = check["skill_level"]
    else:
        check = _run_player_craft(lvl, "woodworking", diff, stat)

    who = f"Worker (Lv{lvl})" if worker_id else f"Self (Lv{lvl})"
    rate_pct = round(check["effective_rate"] * 100, 1)
    xp = xp_gain(lvl, complexity, check["success"], check["quality"])
    attrs = {"complexity": complexity,
             "mastery_rate": rate_pct, "mastery_level": lvl, "mastery_skill": "woodworking"}
    if worker_id:
        attrs["worker_id"] = worker_id
        attrs["crafted_by"] = "worker"
    else:
        attrs["crafted_by"] = "player"

    return make_result(
        success=check["success"],
        effect=f"[{who} — {rate_pct}%] Crafted a sturdy wooden item" if check["success"]
               else f"[{who} — {rate_pct}%] The wood splinters and breaks",
        skill_xp=xp, cooldown=1,
        attributes=attrs,
    )


def _enchanting(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    enchant_power = ctx.get("enchant_power", 1)
    mana = ctx.get("mana", 50)
    mana_cost = 15 * enchant_power
    worker_id = ctx.get("worker_id")

    if mana < mana_cost and not worker_id:
        return make_result(False, f"Not enough mana for enchanting ({mana}/{mana_cost})")

    diff = _difficulty_label(enchant_power)

    if worker_id:
        check = _run_worker_craft(worker_id, "enchanting", diff, stat)
        if check is None:
            return make_result(False, f"Worker {worker_id} not found or can't enchant")
        lvl = check["skill_level"]
    else:
        check = _run_player_craft(lvl, "enchanting", diff, stat)

    effect_power = 0
    if check["success"]:
        effect_power = enchant_power + int(lvl * 0.3)
        if check["quality"] == "critical":
            effect_power = int(effect_power * 1.5)

    who = f"Worker (Lv{lvl})" if worker_id else f"Self (Lv{lvl})"
    rate_pct = round(check["effective_rate"] * 100, 1)
    xp = xp_gain(lvl, enchant_power, check["success"], check["quality"])
    mana_used = mana_cost if not worker_id else 0
    attrs = {"enchant_power": effect_power, "mana_cost": mana_used,
             "mastery_rate": rate_pct, "mastery_level": lvl, "mastery_skill": "enchanting"}
    if worker_id:
        attrs["worker_id"] = worker_id
        attrs["crafted_by"] = "worker"
    else:
        attrs["crafted_by"] = "player"

    return make_result(
        success=check["success"],
        effect=f"[{who} — {rate_pct}%] Item enchanted (power {effect_power})" if check["success"]
               else f"[{who} — {rate_pct}%] Enchantment collapses!",
        skill_xp=xp, cooldown=3,
        attributes=attrs,
    )


SKILLS: dict[str, dict] = {
    "smithing": {"handler": _smithing, "category": "crafting", "description": "Forge and repair metal weapons and armor"},
    "alchemy": {"handler": _alchemy, "category": "crafting", "description": "Brew potions and concoctions"},
    "woodworking": {"handler": _woodworking, "category": "crafting", "description": "Craft wood-based items and structures"},
    "enchanting": {"handler": _enchanting, "category": "crafting", "description": "Infuse items with magical properties"},
}
