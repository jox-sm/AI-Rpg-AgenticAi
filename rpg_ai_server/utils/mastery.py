from __future__ import annotations

import json
import math
import random
from pathlib import Path

_MASTERY_DATA: dict | None = None


def _load_mastery() -> dict:
    global _MASTERY_DATA
    if _MASTERY_DATA is None:
        path = Path(__file__).resolve().parent.parent.parent / "items-db" / "mastery.json"
        if path.exists():
            _MASTERY_DATA = json.loads(path.read_text(encoding="utf-8"))
        else:
            _MASTERY_DATA = {"defaults": {"scaling_factor": 10.5, "min_rate": 0.02, "max_rate": 0.95}, "skills": {}}
    return _MASTERY_DATA


def get_mastery_skills() -> list[dict]:
    data = _load_mastery()
    return [
        {"key": k, "label": v.get("label", k), "stations": v.get("stations", [])}
        for k, v in data.get("skills", {}).items()
    ]


def get_mastery_config(skill_key: str) -> dict | None:
    data = _load_mastery()
    skill = data.get("skills", {}).get(skill_key)
    if not skill:
        return None
    defaults = data.get("defaults", {})
    return {
        "scaling_factor": skill.get("scaling_factor", defaults.get("scaling_factor", 10.5)),
        "min_rate": skill.get("min_rate", defaults.get("min_rate", 0.02)),
        "max_rate": skill.get("max_rate", defaults.get("max_rate", 0.95)),
        "label": skill.get("label", skill_key),
        "stations": skill.get("stations", []),
    }


def base_success_rate(skill_level: int, skill_key: str = "smithing") -> float:
    cfg = get_mastery_config(skill_key)
    if cfg is None:
        cfg = get_mastery_config("smithing")
    sf = cfg["scaling_factor"]
    min_r = cfg["min_rate"]
    max_r = cfg["max_rate"]
    if skill_level <= 0:
        return 0.0
    rate = 1.0 - math.exp(-(skill_level - 1) / sf)
    return max(min_r, min(max_r, rate))


def mastery_check(
    skill_level: int,
    skill_key: str = "smithing",
    difficulty: str = "normal",
    stat_bonus: int = 0,
    modifiers: dict | None = None,
) -> dict:
    cfg = get_mastery_config(skill_key)
    if cfg is None:
        cfg = get_mastery_config("smithing")

    base = base_success_rate(skill_level, skill_key)
    data = _load_mastery()
    skill_cfg = data.get("skills", {}).get(skill_key, {})
    diff_map = skill_cfg.get("difficulty_modifiers", {})
    diff_mult = diff_map.get(difficulty, 1.0)

    stat_mod = 1.0 + stat_bonus * 0.02
    roll = random.random()
    effective_rate = base / diff_mult * stat_mod
    effective_rate = max(0.0, min(0.999, effective_rate))
    success = roll < effective_rate

    quality = "failure"
    if success:
        if roll < effective_rate * 0.1:
            quality = "critical"
        elif roll < effective_rate * 0.35:
            quality = "good"
        else:
            quality = "success"

    return {
        "success": success,
        "quality": quality,
        "roll": round(roll, 4),
        "effective_rate": round(effective_rate, 4),
        "base_rate": round(base, 4),
        "difficulty": difficulty,
        "difficulty_mult": diff_mult,
        "skill_level": skill_level,
        "skill_key": skill_key,
        "stat_bonus": stat_bonus,
    }


def mastery_table(skill_key: str = "smithing", max_level: int = 20) -> list[dict]:
    return [
        {"level": lv, "rate": round(base_success_rate(lv, skill_key) * 100, 1)}
        for lv in range(1, max_level + 1)
    ]
