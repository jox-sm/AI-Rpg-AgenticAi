from __future__ import annotations

import random
from typing import Optional

from .dice_engine import (
    Dice,
    attack_roll as dice_attack_roll,
    probability_of_success,
    roll,
    roll_total,
    roll_with_advantage,
    roll_with_disadvantage,
    success,
    success_with_bonus,
)

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


def resolve_dodge(
    target_dodge: int,
    attacker_accuracy: int = 0,
    modifier: int = 0,
    advantage: bool = False,
    disadvantage: bool = False,
) -> dict:
    if advantage:
        roll_val, r1, r2 = roll_with_advantage(Dice.D20)
    elif disadvantage:
        roll_val, r1, r2 = roll_with_disadvantage(Dice.D20)
    else:
        roll_val = roll_total(Dice.D20)
        r1 = r2 = roll_val

    total = roll_val + modifier
    dc = attacker_accuracy
    dodged = total >= dc if dc > 0 else roll_val >= 10

    return {
        "roll": roll_val,
        "rolls": [r1, r2] if (advantage or disadvantage) else [roll_val],
        "modifier": modifier,
        "total": total,
        "dc": dc,
        "dodged": dodged,
        "dodge_rating": target_dodge,
    }


def resolve_block(
    blocker_defense: int,
    incoming_damage: int,
    block_dice: Dice | int = Dice.D6,
    block_count: int = 1,
    block_bonus: int = 0,
    advantage: bool = False,
    disadvantage: bool = False,
) -> dict:
    if advantage:
        block_roll, r1, r2 = roll_with_advantage(block_dice)
    elif disadvantage:
        block_roll, r1, r2 = roll_with_disadvantage(block_dice)
    else:
        block_roll = roll_total(block_dice)
        r1 = r2 = block_roll

    block_value = block_roll + block_bonus + blocker_defense
    blocked = block_value >= incoming_damage
    remaining = max(0, incoming_damage - block_value)
    reduction_pct = round(min(1.0, block_value / max(incoming_damage, 1)), 2)

    return {
        "block_roll": block_roll,
        "rolls": [r1, r2] if (advantage or disadvantage) else [block_roll],
        "block_bonus": block_bonus,
        "block_value": block_value,
        "incoming_damage": incoming_damage,
        "blocked": blocked,
        "remaining_damage": remaining,
        "reduction_percent": reduction_pct,
    }


def resolve_armor(
    incoming_damage: int,
    armor_rating: int,
    armor_penetration: float = 0.0,
    damage_type: str = "physical",
) -> dict:
    effective_armor = int(armor_rating * (1.0 - min(armor_penetration, 1.0)))
    reduced = max(0, incoming_damage - effective_armor)
    reduction_pct = round(1.0 - (reduced / max(incoming_damage, 1)), 2) if incoming_damage > 0 else 0.0

    return {
        "incoming_damage": incoming_damage,
        "armor_rating": armor_rating,
        "effective_armor": effective_armor,
        "armor_penetration": armor_penetration,
        "damage_after_armor": reduced,
        "reduction_percent": reduction_pct,
    }


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


def full_combat_turn(
    attacker_name: str = "attacker",
    attacker_attack: int = 10,
    attacker_accuracy: int = 0,
    attacker_max_hp: int = 100,
    attacker_current_hp: int = 100,
    attacker_defense: int = 5,
    attacker_dodge: int = 0,
    attacker_statuses: Optional[list[dict]] = None,
    defender_name: str = "defender",
    defender_attack: int = 10,
    defender_accuracy: int = 0,
    defender_max_hp: int = 100,
    defender_current_hp: int = 100,
    defender_armor_class: int = 10,
    defender_dodge: int = 0,
    defender_defense: int = 5,
    defender_type: str = "flesh",
    defender_resistances: Optional[dict[str, float]] = None,
    attacker_damage_type: str = "physical",
    attacker_damage_dice: Dice | int = Dice.D6,
    attacker_damage_count: int = 1,
    attacker_damage_bonus: int = 0,
    attacker_advantage: bool = False,
    attacker_disadvantage: bool = False,
    attacker_modifier: int = 0,
    attacker_crit_threshold: int = 20,
    attacker_crit_mult: float = 2.0,
    attacker_armor_pen: float = 0.0,
    plan_damage_mult: float = 1.0,
    position_mult: float = 1.0,
) -> dict:
    atk_statuses = list(attacker_statuses or [])
    def_statuses: list[dict] = []

    atk_proc = process_status_effects(atk_statuses, attacker_max_hp, attacker_current_hp)
    def_proc = process_status_effects(def_statuses, defender_max_hp, defender_current_hp)

    atk_acc_mult = atk_proc["accuracy_multiplier"]
    atk_dodge_mult = atk_proc["dodge_multiplier"]
    effective_accuracy = int(attacker_accuracy * atk_acc_mult) if atk_acc_mult < 1.0 else attacker_accuracy

    def_dodge_mult = def_proc["dodge_multiplier"]
    def_def_mult = def_proc["defense_multiplier"]
    effective_dodge = int(defender_dodge * def_dodge_mult) if def_dodge_mult < 1.0 else defender_dodge
    effective_def = int(defender_defense * def_def_mult) if def_def_mult < 1.0 else defender_defense

    stunned = any(s["name"] == "stun" for s in atk_statuses)
    if stunned:
        return {
            "turn_summary": f"{attacker_name} is stunned and cannot act!",
            "attacker_hp": atk_proc["new_hp"],
            "defender_hp": def_proc["new_hp"],
            "attack_result": None,
            "attacker_status_phase": atk_proc["statuses"],
            "defender_status_phase": def_proc["statuses"],
            "attacker_dead": atk_proc["dead"],
            "defender_dead": def_proc["dead"],
        }

    attack_result = resolve_attack(
        attacker_attack=attacker_attack,
        attacker_accuracy=effective_accuracy,
        target_armor_class=defender_armor_class,
        target_dodge=effective_dodge,
        damage_type=attacker_damage_type,
        target_type=defender_type,
        target_resistances=defender_resistances,
        damage_dice=attacker_damage_dice,
        damage_count=attacker_damage_count,
        damage_bonus=attacker_damage_bonus,
        advantage=attacker_advantage,
        disadvantage=attacker_disadvantage,
        modifier=attacker_modifier,
        critical_threshold=attacker_crit_threshold,
        crit_multiplier=attacker_crit_mult,
        armor_penetration=attacker_armor_pen,
        plan_damage_mult=plan_damage_mult,
        position_mult=position_mult,
    )

    new_def_hp = def_proc["new_hp"] - attack_result["damage"]
    new_def_hp = max(0, new_def_hp)

    status_result = {"applied": False, "statuses": def_statuses}
    if attack_result["hit"]:
        status_result = apply_status_effect(
            existing_statuses=def_statuses,
            damage_type=attacker_damage_type,
            target_type=defender_type,
        )

    return {
        "turn_summary": (
            f"{attacker_name} attacks {defender_name}: "
            f"{'HIT' if attack_result['hit'] else 'MISS'} "
            f"(rolled {attack_result['roll']} vs DC {attack_result['dc']}) "
            f"{'CRITICAL!' if attack_result['critical'] else ''} "
            f"{'DODGED!' if attack_result['dodged'] else ''} "
            f"for {attack_result['damage']} {attacker_damage_type} damage"
        ),
        "attacker_name": attacker_name,
        "defender_name": defender_name,
        "attacker_hp": atk_proc["new_hp"],
        "defender_hp": new_def_hp,
        "attack_result": attack_result,
        "attacker_status_phase": atk_proc,
        "defender_status_phase": def_proc,
        "status_applied": status_result,
        "attacker_dead": atk_proc["dead"],
        "defender_dead": new_def_hp <= 0,
    }
