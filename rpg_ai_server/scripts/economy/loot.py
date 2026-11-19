from __future__ import annotations

"""Loot parsing, item-db resolution and rarity/tier-weighted rolling."""

import random
from typing import Any, Dict, List, Optional, Tuple

from ...utils.coerce import to_int
from .common import (
    RARITY_LUCK,
    RARITY_ROLL_BONUS,
    TIER_ROLLS,
    _DICE_RE,
    _GOLD_RE,
    _db,
    _enemy_cache,
    _slug,
    normalize_rarity,
    normalize_tier,
)


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
        item = {"item_id": _slug(str(found.get("_src_id") or found.get("name"))),
                "name": str(found.get("name")),
                "quantity": 1,
                "description": str(found.get("Description", ""))[:200],
                "properties": {"rarity": str(found.get("Rarity", fallback_rarity)).lower()}}
        # Carry the DB weapon data into properties (the only inventory keys
        # that survive the model/Redis round-trip). Without this, loot lost
        # its damage/speed/effect forever and equipping had nothing to read.
        dmg = str(found.get("Damage", "") or "").strip()
        if dmg:
            effect = str(found.get("Special Effect", "") or "").strip()
            item["properties"].update({
                "weapon_type": str(found.get("Type", "") or "").strip()[:40].lower(),
                "damage": dmg,
                "speed": str(found.get("Speed", "") or "").strip()[:20].lower(),
                "effect": effect[:80] if effect and effect.lower() != "none" else "",
                "required_level": to_int(found.get("Required Level", 0), 0),
                "required_stats": str(found.get("Required Stats", "") or "").strip()[:60],
                "durability": to_int(found.get("Durability", 0), 0),
            })
        return item
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
