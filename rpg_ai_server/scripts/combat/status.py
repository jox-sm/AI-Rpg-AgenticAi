"""Status effect application and per-turn processing."""
from __future__ import annotations

import random
from typing import Optional

from .common import STATUS_EFFECTS

def apply_status_effect(
    existing_statuses: Optional[list[dict]] = None,
    new_effect: str = "",
    damage_type: str = "",
    target_type: str = "",
    apply_chance: float = 1.0,
    duration_mult: float = 1.0,
) -> dict:
    existing = list(existing_statuses or [])

    if new_effect and new_effect in STATUS_EFFECTS:
        if random.random() > apply_chance:
            return {"applied": False, "statuses": existing, "reason": "apply_chance_failed"}

        effect_template = STATUS_EFFECTS[new_effect]
        turns = max(1, int(effect_template["turns"] * duration_mult))

        if target_type.lower() == "undead" and new_effect in ("poison", "bleed"):
            return {"applied": False, "statuses": existing, "reason": "immune"}

        for i, s in enumerate(existing):
            if s["name"] == new_effect:
                existing[i]["remaining_turns"] = max(existing[i]["remaining_turns"], turns)
                existing[i]["stack"] = existing[i].get("stack", 1) + 1
                return {"applied": True, "refreshed": True, "statuses": existing}

        existing.append({
            "name": new_effect,
            "remaining_turns": turns,
            "stack": 1,
            **{k: v for k, v in effect_template.items() if k != "turns"},
        })
        return {"applied": True, "refreshed": False, "statuses": existing}

    auto_effect = _damage_type_to_effect(damage_type)
    if auto_effect and random.random() < 0.3:
        return apply_status_effect(existing, auto_effect, "", target_type, 1.0, duration_mult)

    return {"applied": False, "statuses": existing, "reason": "no_effect"}


def _damage_type_to_effect(damage_type: str) -> str:
    mapping = {
        "fire": "burn", "poison": "poison", "cold": "freeze",
        "slashing": "bleed", "piercing": "bleed", "lightning": "stun",
        "thunder": "stun", "necrotic": "slow", "psychic": "slow",
    }
    return mapping.get(damage_type.lower(), "")


def process_status_effects(
    statuses: list[dict],
    max_hp: int,
    current_hp: int,
    current_accuracy: float = 1.0,
    current_dodge: float = 1.0,
    current_defense: float = 1.0,
) -> dict:
    total_damage = 0
    total_heal = 0
    expired: list[str] = []
    updated: list[dict] = []
    acc_mult = current_accuracy
    dodge_mult = current_dodge
    def_mult = current_defense

    for s in statuses:
        name = s["name"]
        template = STATUS_EFFECTS.get(name)
        if not template:
            continue

        stack = s.get("stack", 1)
        damage_pct = s.get("damage_pct", template.get("damage_pct", 0.0))
        heal_pct = s.get("heal_pct", template.get("heal_pct", 0.0))

        if damage_pct > 0:
            tick = int(max_hp * damage_pct * stack)
            total_damage += tick

        if heal_pct > 0:
            tick_heal = int(max_hp * heal_pct * stack)
            total_heal += tick_heal

        acc_mult *= (1.0 - s.get("accuracy_reduction", template.get("accuracy_reduction", 0.0)))
        dodge_mult *= (1.0 - s.get("dodge_reduction", template.get("dodge_reduction", 0.0)))
        def_mult *= (1.0 - s.get("defense_reduction", template.get("defense_reduction", 0.0)))

        s["remaining_turns"] -= 1
        if s["remaining_turns"] <= 0:
            expired.append(name)
        else:
            updated.append(s)

    new_hp = current_hp - total_damage + total_heal
    new_hp = max(0, min(max_hp, new_hp))

    return {
        "statuses": updated,
        "expired": expired,
        "tick_damage": total_damage,
        "tick_heal": total_heal,
        "new_hp": new_hp,
        "accuracy_multiplier": round(acc_mult, 2),
        "dodge_multiplier": round(dodge_mult, 2),
        "defense_multiplier": round(def_mult, 2),
        "dead": new_hp <= 0,
    }
