"""Attack resolution: base damage, resistances, multipliers, hit location."""
from __future__ import annotations

import random
from typing import Optional

from ..dice_engine import (
    Dice,
    probability_of_success,
    roll,
    roll_total,
    roll_with_advantage,
    roll_with_disadvantage,
)
from .common import DAMAGE_TYPE_EFFECTIVENESS

def resistance_modifier(
    damage_type: str,
    target_type: str,
    target_resistances: Optional[dict[str, float]] = None,
) -> float:
    mod = DAMAGE_TYPE_EFFECTIVENESS.get(damage_type.lower(), {}).get(target_type.lower(), 1.0)
    if target_resistances:
        custom = target_resistances.get(damage_type.lower())
        if custom is not None:
            mod *= custom
    return mod


def calculate_base_damage(
    attack_power: int,
    target_defense: int,
    armor_penetration: float = 0.0,
    damage_dice: Dice | int = Dice.D6,
    damage_count: int = 1,
    damage_bonus: int = 0,
    crit_multiplier: float = 2.0,
) -> dict:
    dmg_rolls = roll(damage_dice, damage_count)
    rolled = sum(dmg_rolls) + damage_bonus
    effective_def = int(target_defense * (1.0 - armor_penetration))
    raw = max(0, attack_power + rolled - effective_def)
    return {
        "damage_rolls": dmg_rolls,
        "rolled_damage": rolled,
        "effective_defense": effective_def,
        "raw_damage": raw,
    }


def apply_damage_multipliers(
    raw_damage: int,
    damage_type: str,
    target_type: str,
    target_resistances: Optional[dict[str, float]] = None,
    plan_damage_mult: float = 1.0,
    position_mult: float = 1.0,
    status_damage_mult: float = 1.0,
    hit_location_mult: float = 1.0,
) -> dict:
    element_mult = resistance_modifier(damage_type, target_type, target_resistances)
    total_mult = element_mult * plan_damage_mult * position_mult * status_damage_mult * hit_location_mult
    final_damage = max(0, int(raw_damage * total_mult))
    return {
        "elemental_multiplier": round(element_mult, 2),
        "plan_damage_multiplier": plan_damage_mult,
        "position_multiplier": position_mult,
        "status_multiplier": status_damage_mult,
        "hit_location_multiplier": hit_location_mult,
        "total_multiplier": round(total_mult, 2),
        "final_damage": final_damage,
    }


def resolve_attack(
    attacker_attack: int,
    attacker_accuracy: int = 0,
    target_armor_class: int = 10,
    target_dodge: int = 0,
    damage_type: str = "physical",
    target_type: str = "flesh",
    target_resistances: Optional[dict[str, float]] = None,
    damage_power: int = 0,
    damage_dice: Dice | int = Dice.D6,
    damage_count: int = 1,
    damage_bonus: int = 0,
    advantage: bool = False,
    disadvantage: bool = False,
    modifier: int = 0,
    critical_threshold: int = 20,
    crit_multiplier: float = 2.0,
    armor_penetration: float = 0.0,
    plan_damage_mult: float = 1.0,
    position_mult: float = 1.0,
    status_damage_mult: float = 1.0,
    hit_location_mult: float = 1.0,
    dice: Dice | int = Dice.D20,
) -> dict:
    effective_acc = attacker_accuracy + modifier

    if advantage:
        raw_roll, r1, r2 = roll_with_advantage(dice)
        roll_mode = "advantage"
    elif disadvantage:
        raw_roll, r1, r2 = roll_with_disadvantage(dice)
        roll_mode = "disadvantage"
    else:
        raw_roll = roll(dice)[0]
        r1, r2 = raw_roll, raw_roll
        roll_mode = "normal"

    total_hit = raw_roll + effective_acc
    crit = raw_roll >= critical_threshold
    dc = target_armor_class + target_dodge

    if target_dodge > 0:
        dodge_roll = roll_total(Dice.D20)
        dodged = dodge_roll >= target_dodge and not crit
    else:
        dodge_roll = 0
        dodged = False

    hit = (total_hit >= dc or crit) and not dodged

    damage = 0
    hit_location = ""
    if hit:
        base = calculate_base_damage(
            attack_power=damage_power or attacker_attack,
            target_defense=target_armor_class,
            armor_penetration=armor_penetration if not crit else 1.0,
            damage_dice=damage_dice,
            damage_count=damage_count * (2 if crit else 1),
            damage_bonus=damage_bonus,
            crit_multiplier=crit_multiplier,
        )
        mults = apply_damage_multipliers(
            raw_damage=base["raw_damage"],
            damage_type=damage_type,
            target_type=target_type,
            target_resistances=target_resistances,
            plan_damage_mult=plan_damage_mult,
            position_mult=position_mult,
            status_damage_mult=status_damage_mult,
            hit_location_mult=hit_location_mult,
        )
        damage = mults["final_damage"]
        hit_location = _roll_hit_location()

    return {
        "roll": raw_roll,
        "rolls": [r1, r2] if (advantage or disadvantage) else [raw_roll],
        "roll_mode": roll_mode,
        "effective_accuracy": effective_acc,
        "total_hit_roll": total_hit,
        "dc": dc,
        "hit": hit,
        "critical": crit,
        "dodged": dodged,
        "dodge_roll": dodge_roll,
        "damage": damage,
        "hit_location": hit_location,
        "hit_probability": probability_of_success(dc, dice, effective_acc),
        "armor_class": target_armor_class,
        "damage_type": damage_type,
        "target_type": target_type,
    }


def _roll_hit_location() -> str:
    locations = [
        ("head", 0.08), ("neck", 0.03), ("chest", 0.20), ("stomach", 0.10),
        ("left_arm", 0.10), ("right_arm", 0.10), ("left_leg", 0.12), ("right_leg", 0.12),
        ("hand", 0.05), ("foot", 0.05), ("back", 0.10), ("wing", 0.03), ("tail", 0.02),
    ]
    r = random.random()
    cumulative = 0.0
    for name, prob in locations:
        cumulative += prob
        if r < cumulative:
            return name
    return "chest"
