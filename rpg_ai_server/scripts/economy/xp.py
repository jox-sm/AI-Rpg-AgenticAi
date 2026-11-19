from __future__ import annotations

"""Kill-XP formula, participation ticks and level-up promotion."""

from typing import Any, Dict, List

from ...utils.coerce import to_int
from .common import (
    RARITY_XP_MULT,
    TIER_MULT,
    TYPE_MULT,
    normalize_rarity,
    normalize_tier,
    round_half_up,
)


def kill_xp(xp_base: Any, level: Any, rarity: Any, tier: Any = "normal", mtype: Any = "") -> int:
    """Full kill-XP formula. Always >= 1."""
    base = to_int(xp_base, 10)
    lvl = max(1, to_int(level, 1))
    r = normalize_rarity(rarity)
    t = normalize_tier(tier)
    type_mult = TYPE_MULT.get(str(mtype or "").strip().lower(), 1.0)
    return max(1, round_half_up(base * lvl * RARITY_XP_MULT[r] * TIER_MULT[t] * type_mult))


def participation_tick(kill: Any) -> int:
    """XP for a non-killing attack turn: a small fraction of the kill value."""
    return max(1, to_int(kill, 4) // 4)


def apply_level_ups(stats: Dict[str, Any], xp: int) -> List[str]:
    """Apply XP to a character-stats dict with level-ups (returns event lines)."""
    events: List[str] = []
    gain = max(0, to_int(xp))
    if gain <= 0:
        return events
    stats["experience"] = to_int(stats.get("experience", 0)) + gain
    while to_int(stats.get("experience", 0)) >= to_int(stats.get("experience_to_next"), 100):
        stats["experience"] -= to_int(stats.get("experience_to_next"), 100)
        stats["level"] = to_int(stats.get("level"), 1) + 1
        stats["experience_to_next"] = 100 * to_int(stats["level"])
        stats["max_health"] = to_int(stats.get("max_health"), 100) + 10
        stats["health"] = stats["max_health"]
        events.append(f"LEVEL UP -> {stats['level']} (hp restored to {stats['max_health']})")
    return events
