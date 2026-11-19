from __future__ import annotations

"""Shared constants, cached state and low-level primitives for the economy.

Imports point down to `utils` only; xp/loot/difficulty build on these. The
mutable caches live here so every consumer shares the same objects.
"""

import re
from typing import Any, Dict, Optional, Tuple

from ...utils.coerce import clamp_int, to_int

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
        from ...utils.items_db import ItemsDB
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


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "loot"


def parse_level_range(v: Any) -> Tuple[int, int]:
    s = str(v or "1").strip()
    if "-" in s:
        a, _, b = s.partition("-")
        return max(1, to_int(a.strip(), 1)), max(1, to_int(b.strip(), 1))
    return max(1, to_int(s, 1)), max(1, to_int(s, 1))
