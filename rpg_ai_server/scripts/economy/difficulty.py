from __future__ import annotations

"""Adaptive difficulty telemetry and the 1.0x -> 4.0x scaling scalar."""

from typing import Any, Dict, List

from ...utils.coerce import to_int
from .common import normalize_rarity

# One scalar, 1.0x -> 4.0x max, deliberately hard to raise. It drives two
# things at once:
#   1. a signal to the world generator: denser monster packs as it climbs;
#   2. a multiplier on spawned monsters' level AND stats (hp/atk/acc/damage).
#   scalar = min(4.0, 1.0 + heat_pts * HEAT_RATE + max(0, days - 10) * DAY_RATE)
# heat_pts grow per kill, weighted by victim rarity (commons +0.25, a dragon
# +5.0): ~150 common kills AND two months survived to approach the cap.
# One direction only — the world gets meaner, never kinder.
RARITY_DIFF_WEIGHT = {
    "common": 0.25,
    "uncommon": 0.5,
    "rare": 1.0,
    "epic": 2.0,
    "legendary": 5.0,
    "mythic": 8.0,
}
TURNS_PER_DAY = 10
SCALAR_MAX = 4.0
HEAT_RATE = 0.05
DAY_RATE = 0.02
DAY_GRACE = 10


def ensure_difficulty(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """Init/return the adaptive-difficulty tracker inside game_data (idempotent)."""
    if not isinstance(game_data, dict):
        raise TypeError("game_data must be a dict")
    diff = game_data.get("difficulty")
    if not isinstance(diff, dict):
        diff = {"turns": 0, "days": 0, "kills": 0, "deaths": 0,
                "damage_dealt": 0, "damage_taken": 0, "heat_pts": 0.0}
        game_data["difficulty"] = diff
    for k in ("turns", "days", "kills", "deaths", "damage_dealt", "damage_taken"):
        diff[k] = max(0, to_int(diff.get(k, 0)))
    try:
        heat = float(diff.get("heat_pts", 0.0))
    except (TypeError, ValueError):
        heat = 0.0
    if heat == 0.0 and diff["kills"] > 0:
        # Backfill pre-scalar saves as if every old kill was a common.
        heat = diff["kills"] * RARITY_DIFF_WEIGHT["common"]
    diff["heat_pts"] = max(0.0, heat)
    return diff


def advance_day_tracker(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """Age the world one turn: turns+1, days = turns // TURNS_PER_DAY."""
    diff = ensure_difficulty(game_data)
    diff["turns"] += 1
    diff["days"] = diff["turns"] // TURNS_PER_DAY
    return diff


def difficulty_scalar(game_data: Dict[str, Any]) -> float:
    """The 1.0x -> 4.0x adaptive scalar. Slow by design: ~150 common kills
    AND two months survived to approach the cap."""
    diff = ensure_difficulty(game_data)
    days = max(0, to_int(diff.get("days", 0)))
    try:
        heat = max(0.0, float(diff.get("heat_pts", 0.0)))
    except (TypeError, ValueError):
        heat = 0.0
    raw = 1.0 + heat * HEAT_RATE + max(0, days - DAY_GRACE) * DAY_RATE
    return round(min(SCALAR_MAX, raw), 2)


def difficulty_report(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """Snapshot for spawn scaling + tool lines."""
    diff = ensure_difficulty(game_data)
    return {"scalar": difficulty_scalar(game_data),
            "days": int(diff.get("days", 0)), "kills": int(diff.get("kills", 0)),
            "heat_pts": round(float(diff.get("heat_pts", 0.0)), 2)}


def add_kill_heat(game_data: Dict[str, Any], rarity: Any) -> float:
    """Credit a kill toward the scalar, weighted by victim rarity."""
    diff = ensure_difficulty(game_data)
    diff["heat_pts"] = max(0.0, float(diff.get("heat_pts", 0.0))
                           + RARITY_DIFF_WEIGHT.get(normalize_rarity(rarity), 0.25))
    return diff["heat_pts"]


def _side_damage(rounds: List[Dict[str, Any]], side: str) -> int:
    return sum(to_int(r.get("damage", 0)) for r in rounds or []
               if isinstance(r, dict) and r.get("side") == side)


def track_fight(game_data: Dict[str, Any], rounds: List[Dict[str, Any]],
                slain: List[Dict[str, Any]], player_down: bool,
                already_dead: bool) -> Dict[str, Any]:
    """Fold one turn into the difficulty telemetry. Heat credits before the
    kill counter (ensure_difficulty backfills heat-0/kills->0 saves)."""
    diff = ensure_difficulty(game_data)
    diff["damage_dealt"] += _side_damage(rounds, "player")
    diff["damage_taken"] += _side_damage(rounds, "monster")
    slain = [m for m in (slain or []) if isinstance(m, dict)]
    if slain and not player_down:
        for foe in slain:
            add_kill_heat(game_data, foe.get("rarity", "common"))
        diff["kills"] += len(slain)
    if player_down and not already_dead:
        diff["deaths"] += 1
    return diff
