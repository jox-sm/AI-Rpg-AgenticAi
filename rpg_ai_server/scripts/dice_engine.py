from __future__ import annotations

import random
from enum import Enum
from typing import Optional


class Dice(Enum):
    D4 = 4
    D6 = 6
    D8 = 8
    D10 = 10
    D12 = 12
    D20 = 20
    D100 = 100


def roll(dice: Dice | int, count: int = 1) -> list[int]:
    sides = dice.value if isinstance(dice, Dice) else dice
    return [random.randint(1, sides) for _ in range(count)]


def roll_total(dice: Dice | int, count: int = 1) -> int:
    return sum(roll(dice, count))


def roll_with_advantage(dice: Dice | int = Dice.D20) -> tuple[int, int, int]:
    a, b = roll(dice, 2)
    return max(a, b), a, b


def roll_with_disadvantage(dice: Dice | int = Dice.D20) -> tuple[int, int, int]:
    a, b = roll(dice, 2)
    return min(a, b), a, b


def success(roll_value: int, dc: int) -> bool:
    return roll_value >= dc


def success_with_bonus(roll_value: int, dc: int, bonus: int = 0) -> bool:
    return roll_value + bonus >= dc


def probability_of_success(dc: int, dice: Dice | int = Dice.D20, bonus: int = 0) -> float:
    sides = dice.value if isinstance(dice, Dice) else dice
    needed = dc - bonus
    if needed > sides:
        return 0.0
    if needed <= 1:
        return 1.0
    return (sides - needed + 1) / sides


def skill_check(dc: int, bonus: int = 0, dice: Dice | int = Dice.D20) -> dict:
    val = roll_total(dice)
    total = val + bonus
    return {
        "roll": val,
        "bonus": bonus,
        "total": total,
        "dc": dc,
        "success": total >= dc,
        "probability": probability_of_success(dc, dice, bonus),
    }


def attack_roll(
    attack_bonus: int,
    ac: int,
    dice: Dice | int = Dice.D20,
    damage_dice: Dice | int = Dice.D6,
    damage_count: int = 1,
    damage_bonus: int = 0,
    critical_threshold: int = 20,
) -> dict:
    raw = roll(dice)
    val = raw[0]
    total = val + attack_bonus
    crit = val >= critical_threshold
    hit = total >= ac or crit

    damage = 0
    if hit:
        dmg_rolls = roll(damage_dice, damage_count * (2 if crit else 1))
        damage = sum(dmg_rolls) + damage_bonus

    return {
        "roll": val,
        "attack_bonus": attack_bonus,
        "total": total,
        "ac": ac,
        "hit": hit,
        "critical": crit,
        "damage_rolls": dmg_rolls if hit else [],
        "damage": damage,
        "hit_probability": probability_of_success(ac, dice, attack_bonus),
    }


def catch_item(
    catch_rate: float = 0.5,
    bonus: float = 0.0,
    multiplier: float = 1.0,
) -> dict:
    effective_rate = min(max((catch_rate + bonus) * multiplier, 0.0), 1.0)
    rolled = random.random()
    caught = rolled < effective_rate
    return {
        "catch_rate": catch_rate,
        "bonus": bonus,
        "multiplier": multiplier,
        "effective_rate": effective_rate,
        "roll": rolled,
        "caught": caught,
    }


def multiply_chance(base: float, multiplier: float) -> float:
    return min(max(base * multiplier, 0.0), 1.0)
