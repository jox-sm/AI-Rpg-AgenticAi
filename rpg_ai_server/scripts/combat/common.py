"""Shared combat data tables (resistance, status, effect mapping)."""
from __future__ import annotations

DAMAGE_TYPE_EFFECTIVENESS: dict[str, dict[str, float]] = {
    "fire": {"ice": 2.0, "plant": 1.5, "earth": 0.5, "metal": 0.5, "water": 0.5, "flesh": 1.0, "undead": 0.5},
    "cold": {"fire": 0.5, "plant": 2.0, "water": 0.5, "earth": 1.5, "flesh": 1.0, "undead": 1.0},
    "lightning": {"water": 2.0, "metal": 1.5, "earth": 0.5, "air": 0.5, "flesh": 1.0, "construct": 0.5},
    "bludgeoning": {"crystal": 2.0, "bone": 1.5, "construct": 0.5, "flesh": 1.0, "plate": 0.8},
    "slashing": {"flesh": 1.5, "plant": 0.5, "construct": 0.5, "scale": 1.2},
    "piercing": {"flesh": 1.0, "plate": 0.5, "scale": 0.5, "chain": 1.2},
    "radiant": {"undead": 2.0, "fiend": 2.0, "shadow": 1.5, "living": 1.0},
    "necrotic": {"living": 1.5, "undead": 0.0, "construct": 0.0, "fiend": 1.0},
    "force": {"ethereal": 2.0, "construct": 1.5, "physical": 1.0, "undead": 1.5},
    "psychic": {"beast": 0.5, "construct": 0.0, "humanoid": 1.5, "undead": 1.0},
    "thunder": {"crystal": 2.0, "construct": 1.5, "flesh": 1.0, "undead": 1.0},
    "acid": {"metal": 2.0, "organic": 1.5, "construct": 1.0, "flesh": 1.2},
    "poison": {"living": 1.0, "undead": 0.0, "construct": 0.0, "plant": 0.5, "fiend": 0.5},
}

STATUS_EFFECTS: dict[str, dict] = {
    "burn": {"damage_pct": 0.10, "turns": 3, "accuracy_reduction": 0.0, "defense_reduction": 0.0},
    "poison": {"damage_pct": 0.05, "turns": 5, "accuracy_reduction": 0.0, "defense_reduction": 0.0},
    "stun": {"damage_pct": 0.0, "turns": 1, "accuracy_reduction": 1.0, "defense_reduction": 0.5},
    "freeze": {"damage_pct": 0.0, "turns": 2, "accuracy_reduction": 0.5, "defense_reduction": 0.3},
    "bleed": {"damage_pct": 0.08, "turns": 4, "accuracy_reduction": 0.0, "defense_reduction": 0.0},
    "blind": {"damage_pct": 0.0, "turns": 2, "accuracy_reduction": 0.5, "defense_reduction": 0.0},
    "slow": {"damage_pct": 0.0, "turns": 3, "accuracy_reduction": 0.0, "defense_reduction": 0.0, "dodge_reduction": 0.5},
    "haste": {"damage_pct": 0.0, "turns": 3, "accuracy_bonus": 0.5, "dodge_bonus": 0.3},
    "regen": {"heal_pct": 0.08, "turns": 3},
    "shield": {"damage_pct": 0.0, "turns": 2, "defense_bonus": 0.5},
}

EFFECT_TO_DAMAGE_TYPE: dict[str, str] = {
    "burn": "fire",
    "poison": "poison",
    "freeze": "cold",
    "bleed": "slashing",
}
