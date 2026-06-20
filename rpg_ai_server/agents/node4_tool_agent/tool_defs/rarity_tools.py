from __future__ import annotations

import json
import math
import random
from typing import Optional

from langchain_core.tools import tool

RARITY_TIERS = [
    {"name": "common",    "mult": 1.0,  "label": "Common"},
    {"name": "uncommon",  "mult": 1.15, "label": "Uncommon"},
    {"name": "rare",      "mult": 1.3,  "label": "Rare"},
    {"name": "fable",     "mult": 1.5,  "label": "Fable"},
    {"name": "epic",      "mult": 1.8,  "label": "Epic"},
    {"name": "mythical",  "mult": 2.3,  "label": "Mythical"},
    {"name": "secret",    "mult": 4.0,  "label": "Secret"},
]

BASE_PROBABILITIES = {
    "common":    50.0,
    "uncommon":  30.0,
    "rare":      12.0,
    "fable":      5.0,
    "epic":       2.5,
    "mythical":   0.49,
    "secret":     0.01,
}


def _calc_rarity_chance(
    base_tier: str,
    blacksmith_skill: int = 0,
    luck_rating: int = 0,
    fame: int = 0,
    item_level: int = 1,
    worker_quality: str = "standard",
    has_luck_charm: bool = False,
    has_luck_stone: bool = False,
    materials_quality: str = "standard",
) -> dict:
    tiers = [t["name"] for t in RARITY_TIERS]
    if base_tier not in tiers:
        base_tier = "common"
    base_idx = tiers.index(base_tier)

    worker_mods = {"poor": -0.3, "standard": 0.0, "skilled": 0.3, "master": 0.7, "legendary": 1.5}
    material_mods = {"poor": -0.2, "standard": 0.0, "good": 0.2, "fine": 0.5, "perfect": 1.0}

    luck_bonus = luck_rating * 0.05
    fame_bonus = fame * 0.03
    skill_bonus = blacksmith_skill * 0.04
    worker_mult = 1.0 + worker_mods.get(worker_quality, 0.0)
    material_mult = 1.0 + material_mods.get(materials_quality, 0.0)
    charm_bonus = 0.5 if has_luck_charm else 0.0
    stone_bonus = 1.0 if has_luck_stone else 0.0

    total_bonus = luck_bonus + fame_bonus + skill_bonus + charm_bonus + stone_bonus
    combined_mult = worker_mult * material_mult

    results = []
    for i, tier in enumerate(tiers):
        if i < base_idx:
            results.append({"tier": tier, "mult": RARITY_TIERS[i]["mult"], "chance": 0.0})
            continue
        if i == base_idx:
            prob = BASE_PROBABILITIES[tier]
        else:
            prob = BASE_PROBABILITIES.get(tier, 0.0)

        prob = prob * combined_mult + total_bonus

        if prob > 0 and i > base_idx:
            higher_probs = sum(BASE_PROBABILITIES.get(t, 0.0) for t in tiers[i:])
            if higher_probs > 0:
                shift = (total_bonus + prob * (combined_mult - 1)) * 0.1
                prob = max(0.0, prob + shift)

        results.append({"tier": tier, "mult": RARITY_TIERS[i]["mult"], "chance": round(prob, 4)})

    total_chance = sum(r["chance"] for r in results)
    if total_chance > 0:
        for r in results:
            r["chance"] = round(r["chance"] / total_chance * 100, 4)

    return {
        "base_tier": base_tier,
        "tiers": results,
        "modifiers": {
            "luck_bonus": round(luck_bonus, 2),
            "fame_bonus": round(fame_bonus, 2),
            "skill_bonus": round(skill_bonus, 2),
            "worker_mult": round(worker_mult, 2),
            "material_mult": round(material_mult, 2),
            "charm_bonus": charm_bonus,
            "stone_bonus": stone_bonus,
            "total_bonus": round(total_bonus, 2),
            "combined_mult": round(combined_mult, 2),
        },
    }


def _roll_rarity(chance_data: dict) -> dict:
    roll = random.random() * 100
    cumulative = 0.0
    chosen = chance_data["tiers"][0]
    for t in chance_data["tiers"]:
        cumulative += t["chance"]
        if roll <= cumulative:
            chosen = t
            break
    return {
        "roll": round(roll, 4),
        "result_tier": chosen["tier"],
        "result_mult": chosen["mult"],
        "result_label": next(r["label"] for r in RARITY_TIERS if r["name"] == chosen["tier"]),
    }


@tool
async def rarity_enhancer(
    base_stats_json: str,
    base_tier: str = "common",
    blacksmith_skill: int = 0,
    luck_rating: int = 0,
    fame: int = 0,
    item_level: int = 1,
    worker_quality: str = "standard",
    materials_quality: str = "standard",
    has_luck_charm: bool = False,
    has_luck_stone: bool = False,
    roll_dice: bool = True,
) -> str:
    """Roll for item rarity enhancement. Higher tiers give better stat multipliers.
    Common=x1, Uncommon=x1.15, Rare=x1.3, Fable=x1.5, Epic=x1.8, Mythical=x2.3, Secret=x4.
    Secret items are 0.01% base — boost odds with luck charms, stones, skilled blacksmiths, fame.

    Args:
        base_stats_json: JSON of base item stats to enhance
        base_tier: Starting rarity tier (common, uncommon, rare, fable, epic, mythical, secret)
        blacksmith_skill: Crafting skill level (0-100)
        luck_rating: Character's luck stat (0-30)
        fame: Character's fame/reputation (0-100)
        item_level: Item level requirement
        worker_quality: Facility quality (poor, standard, skilled, master, legendary)
        materials_quality: Input material quality (poor, standard, good, fine, perfect)
        has_luck_charm: Whether a luck charm is consumed
        has_luck_stone: Whether a luck stone is consumed
        roll_dice: If True, rolls against probability. If False, returns odds only.
    """
    try:
        base_stats = json.loads(base_stats_json) if isinstance(base_stats_json, str) else base_stats_json
    except (json.JSONDecodeError, TypeError):
        base_stats = {}

    chance_data = _calc_rarity_chance(
        base_tier=base_tier,
        blacksmith_skill=blacksmith_skill,
        luck_rating=luck_rating,
        fame=fame,
        item_level=item_level,
        worker_quality=worker_quality,
        has_luck_charm=has_luck_charm,
        has_luck_stone=has_luck_stone,
        materials_quality=materials_quality,
    )

    result = {
        "odds": chance_data,
        "scenario": "",
    }

    if roll_dice:
        roll_result = _roll_rarity(chance_data)
        result["roll"] = roll_result

        mult = roll_result["result_mult"]
        tier = roll_result["result_tier"]
        label = roll_result["result_label"]

        enhanced = {}
        for key, val in base_stats.items():
            if isinstance(val, (int, float)):
                enhanced[key] = round(val * mult, 2) if isinstance(val, float) else int(val * mult)
            else:
                enhanced[key] = val
        enhanced["rarity"] = label
        enhanced["rarity_tier"] = tier
        enhanced["rarity_mult"] = mult

        result["enhanced_stats"] = enhanced
        result["scenario"] = (
            f"Rolled {roll_result['roll']:.2f}% -> {label} (x{mult}). "
            f"Stats boosted accordingly."
        )

        if tier in ("secret", "mythical"):
            result["scenario"] += " A legendary shimmer surrounds the item!"
    else:
        odds_summary = ", ".join(
            f"{t['tier']}: {t['chance']:.2f}%"
            for t in chance_data["tiers"]
            if t["chance"] > 0
        )
        result["scenario"] = f"Estimated odds: {odds_summary}"

    return json.dumps(result, indent=2)
