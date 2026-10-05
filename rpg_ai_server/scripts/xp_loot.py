from __future__ import annotations

"""XP + loot economy (pure, deterministic given seeded random).

XP formula:  kill_xp = round_half_up(xp_base * level * RARITY_XP_MULT * TIER_MULT * TYPE_MULT)
  e.g. common goblin: 10 * 1 * 0.25 = 2.5 -> 3; uncommon orc: 35 * 4 * 0.5 = 70.
Non-killing attack turns grant a participation tick = max(1, kill_xp // 4).

Loot: parsed from the item-db enemy "Loot" string ("Rusty Dagger, 5 Gold"),
resolved through ItemsDB, rolled with rarity luck. Higher rarity = more rolls
at better odds. No DB row -> rarity-pool fallback / plain gold.

Stat scale (integers; single digits are baby-tier, not hero-tier):
   1-2  helpless infant   (invalid for spawns — clamped up)
   3-5  baby zombie / small child
   6-7  weak
   8-12 average adult
  13-15 trained / veteran
  16-19 heroic
  20-30 legendary (mortal ceiling)
"""

import random
import re
from typing import Any, Dict, List, Optional, Tuple

from ..utils.coerce import clamp_int, to_int

RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary", "mythic"]

RARITY_XP_MULT = {
    "common": 0.25,
    "uncommon": 0.5,
    "rare": 1.0,
    "epic": 2.0,
    "legendary": 4.0,
    "mythic": 8.0,
}

RARITY_LUCK = {
    "common": 0.0,
    "uncommon": 0.10,
    "rare": 0.20,
    "epic": 0.30,
    "legendary": 0.45,
    "mythic": 0.60,
}

RARITY_ROLL_BONUS = {
    "common": 0,
    "uncommon": 0,
    "rare": 0,
    "epic": 1,
    "legendary": 1,
    "mythic": 2,
}

TIER_MULT = {"normal": 1.0, "elite": 1.5, "boss": 3.0}
TIER_ROLLS = {"normal": 1, "elite": 2, "boss": 3}

# ── Adaptive difficulty (RE4-style scaling box) ──
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

TYPE_MULT = {
    "dragon": 2.0,
    "giant": 1.5,
    "fiend": 1.5,
    "undead": 1.25,
    "construct": 1.25,
    "boss": 3.0,
}

STAT_MIN = 3
STAT_MAX = 30

_GOLD_RE = re.compile(r"^\s*(\d+)\s+gold\s*$", re.IGNORECASE)
_DICE_RE = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*(?:\+\s*(\d+))?\s*$", re.IGNORECASE)

_enemy_cache: Dict[str, Optional[Dict[str, Any]]] = {}
_items_db = None


def _db():
    global _items_db
    if _items_db is None:
        from ..utils.items_db import ItemsDB
        _items_db = ItemsDB()
    return _items_db


def round_half_up(x: float) -> int:
    import math
    return int(math.floor(float(x) + 0.5))


def clamp_stat(v: Any, lo: int = STAT_MIN, hi: int = STAT_MAX) -> int:
    """Normalize a stat into the mortal scale (agility 1 = baby zombie -> 3)."""
    return clamp_int(v, lo, hi, default=10)


def normalize_rarity(rarity: Any) -> str:
    r = str(rarity or "common").strip().lower()
    return r if r in RARITY_XP_MULT else "common"


def normalize_tier(tier: Any) -> str:
    t = str(tier or "normal").strip().lower()
    return t if t in TIER_MULT else "normal"


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


def roll_qty(spec: Any) -> int:
    """Parse '5' or dice notation '2d6+1' into a rolled quantity."""
    s = str(spec or "1").strip()
    if s.isdigit():
        return max(1, int(s))
    m = _DICE_RE.match(s)
    if m:
        n, sides, bonus = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        n = min(max(n, 1), 20)
        sides = min(max(sides, 2), 100)
        return max(1, sum(random.randint(1, sides) for _ in range(n)) + bonus)
    return 1


def parse_loot_string(loot: Any) -> List[Tuple[str, str]]:
    """'Rusty Dagger, Goblin Ear, 5 Gold' -> [('item','Rusty Dagger'),...,('gold','5')]."""
    if not isinstance(loot, str) or not loot.strip():
        return []
    out: List[Tuple[str, str]] = []
    for part in loot.split(","):
        part = part.strip()
        if not part:
            continue
        g = _GOLD_RE.match(part)
        if g:
            out.append(("gold", g.group(1)))
        else:
            out.append(("item", part))
    return out


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "loot"


def resolve_loot_entry(kind: str, spec: str, fallback_rarity: str = "common") -> Dict[str, Any]:
    """Resolve one loot entry to an inventory-ready dict (DB hit or named scrap)."""
    if kind == "gold":
        return {"item_id": "gold", "name": "Gold", "quantity": roll_qty(spec),
                "description": "Coins.", "properties": {"currency": True}}
    found = None
    try:
        found = _db().get_by_name(spec)
    except Exception:
        found = None
    if isinstance(found, dict) and found.get("name"):
        return {"item_id": _slug(str(found.get("_src_id") or found.get("name"))),
                "name": str(found.get("name")),
                "quantity": 1,
                "description": str(found.get("Description", ""))[:200],
                "properties": {"rarity": str(found.get("Rarity", fallback_rarity)).lower()}}
    return {"item_id": _slug(spec), "name": spec, "quantity": 1,
            "description": "Taken from a fallen foe.",
            "properties": {"rarity": fallback_rarity, "scrap": True}}


def enemy_db_row(name: str) -> Optional[Dict[str, Any]]:
    """Item-db enemy row for a monster name: exact match, else contains-match, else None."""
    key = str(name or "").strip().lower()
    if not key:
        return None
    if key in _enemy_cache:
        return _enemy_cache[key]
    try:
        rows = _db().filter(_file="enemies") or []
    except Exception:
        rows = []
    exact = next((r for r in rows if isinstance(r, dict) and str(r.get("name", "")).strip().lower() == key), None)
    if exact is not None:
        _enemy_cache[key] = exact
        return exact
    fuzzy = next((r for r in rows if isinstance(r, dict)
                  and (key in str(r.get("name", "")).strip().lower()
                       or str(r.get("name", "")).strip().lower() in key)), None)
    _enemy_cache[key] = fuzzy
    return fuzzy


def parse_level_range(v: Any) -> Tuple[int, int]:
    s = str(v or "1").strip()
    if "-" in s:
        a, _, b = s.partition("-")
        return max(1, to_int(a.strip(), 1)), max(1, to_int(b.strip(), 1))
    return max(1, to_int(s, 1)), max(1, to_int(s, 1))


def roll_loot(sheet: Dict[str, Any], rng: Any = random) -> List[Dict[str, Any]]:
    """Roll kill loot for a monster sheet. Rarity luck + tier rolls, DB probabilities."""
    rarity = normalize_rarity(sheet.get("rarity", "common"))
    tier = normalize_tier(sheet.get("tier", "normal"))
    luck = RARITY_LUCK[rarity]
    rolls = TIER_ROLLS[tier] + RARITY_ROLL_BONUS[rarity]
    candidates = parse_loot_string(sheet.get("loot"))
    if not candidates:
        try:
            pool = _db().by_rarity(rarity, limit=20) or []
        except Exception:
            pool = []
        candidates = [("item", str(p.get("name"))) for p in pool[:10]
                      if isinstance(p, dict) and p.get("name")]
    if not candidates:
        candidates = [("gold", "2d6")]
    drops: List[Dict[str, Any]] = []
    for _ in range(max(1, rolls)):
        kind, spec = rng.choice(candidates)
        if rng.random() < 0.5 + luck:
            drops.append(resolve_loot_entry(kind, spec, fallback_rarity=rarity))
    return drops


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


def award_for_kills(slain: List[Dict[str, Any]], new_stats: Dict[str, Any],
                    player_down: bool) -> Tuple[int, list, list]:
    """Summed kill XP + per-corpse loot rolls + level-ups (all skipped when down)."""
    award, loot = 0, []
    if slain and not player_down:
        for foe in slain:
            if not isinstance(foe, dict):
                continue
            award += kill_xp(foe.get("xp_base", 10), foe.get("level", 1),
                             foe.get("rarity", "common"), foe.get("tier", "normal"),
                             foe.get("type", ""))
            try:
                loot.extend(roll_loot(foe))
            except Exception:
                pass
    events = apply_level_ups(new_stats, award) if award > 0 else []
    return award, loot, events


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


def merge_loot(inventory: Any, loot: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Append loot to inventory, stacking matching item_ids (gold stacks)."""
    inv = [dict(i) if isinstance(i, dict) else i for i in (inventory or [])]
    for drop in loot or []:
        if not isinstance(drop, dict):
            continue
        did = str(drop.get("item_id", ""))
        qty = to_int(drop.get("quantity", 1), 1)
        for entry in inv:
            if isinstance(entry, dict) and str(entry.get("item_id", "")) == did:
                entry["quantity"] = to_int(entry.get("quantity", 1), 1) + qty
                break
        else:
            item = dict(drop)
            item["quantity"] = qty
            inv.append(item)
    return inv


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
