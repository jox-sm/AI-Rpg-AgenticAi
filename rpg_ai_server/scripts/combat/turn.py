"""Top-level full combat turn orchestration."""
from __future__ import annotations

from typing import Optional

from ..dice_engine import Dice
from .damage import resolve_attack
from .status import apply_status_effect, process_status_effects

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
