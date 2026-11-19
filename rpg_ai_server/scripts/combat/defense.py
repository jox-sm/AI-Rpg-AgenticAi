"""Defensive resolution: dodge, block, armor."""
from __future__ import annotations

from ..dice_engine import Dice, roll_total, roll_with_advantage, roll_with_disadvantage

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
