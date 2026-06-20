from __future__ import annotations

import math


def mastery_rate(
    skill_level: int,
    scaling_factor: float = 10.5,
    min_rate: float = 0.02,
    max_rate: float = 0.95,
    player_level: int = 1,
    level_boost: float = 0.0,
) -> float:
    if skill_level <= 0:
        return 0.0
    level_bonus = player_level * 0.005 * level_boost
    effective_lv = skill_level + level_bonus
    rate = 1.0 - math.exp(-(effective_lv - 1) / scaling_factor)
    return max(min_rate, min(max_rate, rate))


def difficulty_multiplier(
    difficulty: str,
    base_modifiers: dict[str, float] | None = None,
) -> float:
    if base_modifiers is None:
        base_modifiers = {
            "trivial": 0.5, "easy": 0.75, "normal": 1.0,
            "hard": 1.3, "very_hard": 1.7, "legendary": 2.2,
        }
    return base_modifiers.get(difficulty, 1.0)


def effective_rate(
    skill_level: int,
    scaling_factor: float = 10.5,
    min_rate: float = 0.02,
    max_rate: float = 0.95,
    difficulty: str = "normal",
    difficulty_modifiers: dict[str, float] | None = None,
    stat_bonus: int = 0,
    player_level: int = 1,
    level_boost: float = 0.0,
) -> float:
    base = mastery_rate(skill_level, scaling_factor, min_rate, max_rate, player_level, level_boost)
    diff_mult = difficulty_multiplier(difficulty, difficulty_modifiers)
    stat_mod = 1.0 + stat_bonus * 0.02
    rate = base / diff_mult * stat_mod
    return max(0.0, min(0.999, rate))


def quality_from_roll(roll: float, effective_rate: float) -> str:
    if roll < effective_rate * 0.1:
        return "critical"
    if roll < effective_rate * 0.35:
        return "good"
    return "success"


def mastery_table(
    skill_level: int,
    scaling_factor: float = 10.5,
    min_rate: float = 0.02,
    max_rate: float = 0.95,
    max_display_levels: int = 20,
    player_level: int = 1,
    level_boost: float = 0.0,
) -> list[dict]:
    return [
        {
            "level": lv,
            "rate": round(
                mastery_rate(lv, scaling_factor, min_rate, max_rate, player_level, level_boost) * 100, 1
            ),
        }
        for lv in range(1, max_display_levels + 1)
    ]


def level_to_scaling(player_level: int, base_sf: float = 10.5) -> float:
    return max(5.0, base_sf - player_level * 0.2)


def level_to_min_rate(player_level: int, base_min: float = 0.02) -> float:
    return max(0.005, base_min - player_level * 0.001)


def level_to_max_rate(player_level: int, base_max: float = 0.95) -> float:
    return min(0.999, base_max + player_level * 0.002)
