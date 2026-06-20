from __future__ import annotations

import math
import random
from typing import Any, Optional


_DC_TO_DIFFICULTY = {
    3: "trivial", 5: "trivial", 7: "easy", 8: "easy",
    10: "normal", 12: "normal", 13: "hard", 15: "hard",
    17: "very_hard", 18: "very_hard", 20: "legendary", 22: "legendary",
}


def _nearest_difficulty(dc: int) -> str:
    keys = sorted(_DC_TO_DIFFICULTY.keys())
    nearest = min(keys, key=lambda k: abs(k - dc))
    return _DC_TO_DIFFICULTY[nearest]


def success_check(
    skill_level: float,
    difficulty: int = 10,
    stat_bonus: int = 0,
    modifier: int = 0,
    mastery_key: Optional[str] = None,
) -> dict:
    if mastery_key:
        from ..utils.mastery import mastery_check
        diff_label = _nearest_difficulty(difficulty)
        result = mastery_check(int(skill_level), mastery_key, diff_label, stat_bonus)
        margin_raw = result["effective_rate"] - result["roll"]
        margin = int(margin_raw * 100)
        return {
            "roll": result["roll"],
            "total": result["roll"],
            "dc": difficulty,
            "success": result["success"],
            "margin": max(margin, 0) if result["success"] else min(margin, 0),
            "quality": result["quality"],
            "mastery_rate": result.get("effective_rate", 0),
            "mastery_key": mastery_key,
        }
    roll = random.randint(1, 20) + int(skill_level) + stat_bonus + modifier
    success = roll >= difficulty
    margin = roll - difficulty
    return {
        "roll": roll - int(skill_level) - stat_bonus - modifier,
        "total": roll,
        "dc": difficulty,
        "success": success,
        "margin": margin,
        "quality": "critical" if margin >= 10 else ("good" if margin >= 5 else ("success" if success else "failure")),
    }


def damage_formula(
    base_damage: int,
    skill_level: float,
    stat_modifier: int = 0,
    multiplier: float = 1.0,
    variance: float = 0.2,
) -> int:
    bonus = int(skill_level * 0.5) + stat_modifier
    raw = (base_damage + bonus) * multiplier
    v = 1.0 + random.uniform(-variance, variance)
    return max(1, int(raw * v))


def xp_gain(
    skill_level: float,
    difficulty_mult: float = 1.0,
    success: bool = True,
    quality: str = "success",
) -> float:
    if not success:
        return round(0.05 * difficulty_mult, 3)
    base = 0.1 + (0.5 / (1 + skill_level * 0.1))
    quality_mult = {"failure": 0.0, "success": 1.0, "good": 1.5, "critical": 2.5}
    return round(base * difficulty_mult * quality_mult.get(quality, 1.0), 3)


def make_result(
    success: bool,
    effect: str = "",
    damage: int = 0,
    damage_type: str = "",
    healing: int = 0,
    skill_xp: float = 0.0,
    cooldown: int = 0,
    status_effects: Optional[list[str]] = None,
    attributes: Optional[dict[str, Any]] = None,
) -> dict:
    result: dict[str, Any] = {
        "success": success,
        "effect": effect,
        "damage": damage,
        "damage_type": damage_type,
        "healing": healing,
        "skill_xp": skill_xp,
        "cooldown": cooldown,
        "status_effects": status_effects or [],
    }
    if attributes:
        result["attributes"] = attributes
    return result
