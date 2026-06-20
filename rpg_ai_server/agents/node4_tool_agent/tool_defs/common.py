from __future__ import annotations

from typing import Any, Dict, List

from ....schemas.enums import DamageType, DiceType, SkillType
from ....schemas.types import InventoryItem
from ....utils.items_db import ItemsDB

_ITEMS_DB = ItemsDB()

DICE_MAP: Dict[DiceType, int] = {
    DiceType.D4: 4,
    DiceType.D6: 6,
    DiceType.D8: 8,
    DiceType.D10: 10,
    DiceType.D12: 12,
    DiceType.D20: 20,
    DiceType.D100: 100,
}

STAT_CAP_TABLE: Dict[int, int] = {
    1: 10, 2: 12, 3: 14, 4: 16, 5: 18,
    6: 20, 7: 22, 8: 24, 9: 26, 10: 30,
}

MONSTER_DIFFICULTY = {
    "rat": {"exp": 10, "level": 1},
    "goblin": {"exp": 50, "level": 2},
    "skeleton": {"exp": 75, "level": 3},
    "zombie": {"exp": 80, "level": 3},
    "wolf": {"exp": 100, "level": 4},
    "bandit": {"exp": 120, "level": 4},
    "bear": {"exp": 200, "level": 5},
    "ogre": {"exp": 300, "level": 6},
    "wraith": {"exp": 400, "level": 7},
    "troll": {"exp": 500, "level": 8},
    "golem": {"exp": 800, "level": 10},
    "dragon_young": {"exp": 1500, "level": 12},
    "lich": {"exp": 2000, "level": 14},
    "dragon_adult": {"exp": 5000, "level": 18},
    "dragon_ancient": {"exp": 15000, "level": 25},
}

PLAN_QUALITY_BONUSES = {
    "none": {"advantage_bonus": -4, "damage_mult": 0.5, "desc": "No plan, just attacking recklessly"},
    "reckless": {"advantage_bonus": -4, "damage_mult": 0.5, "desc": "Reckless attack with no strategy"},
    "poor": {"advantage_bonus": -2, "damage_mult": 0.7, "desc": "Bad plan that makes the situation worse"},
    "average": {"advantage_bonus": 0, "damage_mult": 1.0, "desc": "Standard attack, nothing special"},
    "good": {"advantage_bonus": 2, "damage_mult": 1.3, "desc": "Decent plan with some tactical thought"},
    "excellent": {"advantage_bonus": 4, "damage_mult": 1.6, "desc": "Smart plan exploiting enemy weaknesses"},
    "genius": {"advantage_bonus": 6, "damage_mult": 2.0, "desc": "Brilliant trap or masterful strategy"},
}

ORGAN_HIT_MULTIPLIERS = {
    "eye": 0.3, "head": 0.5, "neck": 0.4, "heart": 0.2,
    "leg": 0.6, "arm": 0.7, "wing": 0.5, "tail": 0.8, "core": 0.25,
}

_CATEGORY_WEIGHTS = {
    "weapon": 3.0, "armour": 15.0, "armor": 15.0, "potion": 0.5, "food": 0.5,
    "material": 2.0, "tool": 4.0, "book": 1.0, "loot": 0.1, "quest": 0.0,
    "misc": 1.0, "scroll": 0.2, "ring": 0.1, "gem": 0.2, "ingredient": 0.3,
    "sword": 3.0, "dagger": 1.5, "bow": 2.0, "crossbow": 5.0, "axe": 4.0,
    "mace": 5.0, "hammer": 6.0, "spear": 3.0, "staff": 3.0, "shield": 8.0,
    "helmet": 8.0, "boots": 3.0, "gloves": 2.0, "chestplate": 20.0,
    "plate": 18.0, "mail": 12.0, "leather": 5.0,
    "mining": 4.0, "gathering": 1.5, "crafting": 3.0, "fishing": 2.0,
    "cooking": 3.0, "medical": 0.5, "smelting": 5.0, "woodworking": 3.0,
}


def item_weight(item: dict) -> float:
    raw = item.get("weight") or item.get("Weight") or 0
    if raw and isinstance(raw, (int, float)):
        return float(raw)
    cat = str(item.get("category", item.get("Category", item.get("Type", "")))).lower()
    for key, w in _CATEGORY_WEIGHTS.items():
        if key in cat:
            return w
    if "log" in item.get("name", "").lower():
        return 5.0
    if "ingot" in item.get("name", "").lower():
        return 3.0
    return 1.0


def container_reduction(inventory: list, container_name: str) -> float:
    for item in inventory:
        if item.name == container_name and item.properties:
            return item.properties.get("weight_reduction", item.properties.get("Weight Reduction", 0.1))
    return 1.0


def calc_load(inventory: list) -> float:
    total = 0.0
    for item in inventory:
        if item.stored_in:
            mult = container_reduction(inventory, item.stored_in)
            total += item.weight * item.quantity * mult
        else:
            total += item.weight * item.quantity
    return total


def load_status(inventory: list, capacity: float) -> dict:
    load = calc_load(inventory)
    pct = (load / capacity * 100) if capacity > 0 else 100
    status = "light"
    if pct >= 90:
        status = "overloaded"
    elif pct >= 70:
        status = "heavy"
    elif pct >= 40:
        status = "moderate"
    return {"load": round(load, 1), "capacity": capacity, "pct": round(pct, 1), "status": status}
