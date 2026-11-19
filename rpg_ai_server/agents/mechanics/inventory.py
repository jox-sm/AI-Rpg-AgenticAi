"""Inventory sub-node: snapshot items; handle the equip action."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ...utils.coerce import as_dict, clamp_int, to_int

EQUIP_RE = re.compile(
    r"\bequip(?:ing|ment)?\s+(?:the\s+|my\s+|a\s+|an\s+)?(?P<target>[a-z][a-z' \-]{1,60})",
    re.IGNORECASE)
UNEQUIP_RE = re.compile(r"\b(?:unequip|stow|sheathe|holster|put\s+away)\b", re.IGNORECASE)
_DMG_RE = re.compile(r"^\s*(\d{1,2})\s*d\s*(\d{1,3})\s*([+-]\s*\d{1,3})?\s*$")


def _item_dict(item: Any) -> Dict[str, Any]:
    """Inventory slot -> plain dict (models only read like models)."""
    return item if isinstance(item, dict) else (as_dict(item) or {})


def _weapon_damage(spec: Any) -> tuple[int, int, int]:
    """'1d4+2' -> (sides, count, bonus); unparseable -> unarmed (6, 1, 2)."""
    m = _DMG_RE.match(str(spec or "").strip())
    if not m:
        return (6, 1, 2)
    count = clamp_int(m.group(1), 1, 12, 1)
    sides = clamp_int(m.group(2), 4, 100, 6)
    bonus = to_int((m.group(3) or "0").replace(" ", ""), 0)
    return (sides, count, bonus)


def _equipped_weapon(inv: Any) -> Optional[Dict[str, Any]]:
    """First actively equipped weapon — combat reads its damage dice from here.

    The equipped flag lives in ``properties``: unknown model keys are dropped
    on the model/Redis round-trip, but ``properties`` is a real model field.
    """
    for raw in inv or []:
        item = _item_dict(raw)
        props = item.get("properties") or {}
        if not isinstance(props, dict):
            continue
        if props.get("weapon_type") and props.get("equipped") and props.get("damage"):
            return item
    return None


def _weapon_stats_note(weapon: Dict[str, Any]) -> Dict[str, Any]:
    """Human-readable loadout line for the mechanics summary."""
    props = weapon.get("properties") or {}
    parts = [str(props.get("weapon_type", "") or "").strip(),
             str(props.get("damage", "?") or "").strip(),
             str(props.get("speed", "") or "").strip()]
    if props.get("effect"):
        parts.append(f"effect {str(props['effect']).lower().strip()}")
    return {"name": str(weapon.get("name", "?")),
            "spec": ", ".join(p for p in parts if p),
            "required_level": to_int(props.get("required_level", 0), 0)}


def _pick_equip_target(items: List[Dict[str, Any]], wanted: str) -> Optional[Dict[str, Any]]:
    """First weapon matching the request; a lone unequipped weapon if generic."""
    has_name = wanted and wanted != "weapon"
    if has_name:
        for item in items:
            props = item.get("properties") or {}
            name = str(item.get("name", "")).lower()
            if props.get("weapon_type") and (wanted in name or name in wanted):
                return item
        for item in items:
            props = item.get("properties") or {}
            wtype = str(props.get("weapon_type", "")).lower()
            if wtype and (wanted in wtype or wtype in wanted):
                return item
        return None
    loose = [item for item in items
             if (item.get("properties") or {}).get("weapon_type")
             and not (item.get("properties") or {}).get("equipped")]
    return loose[0] if len(loose) == 1 else None


async def _inventory_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    """Inventory pass: snapshot, plus one real behavior — the equip action.

    'equip <item>' flips the weapon's equipped flag (unequipping other
    weapons); combat then rolls the weapon's damage instead of fists.
    """
    try:
        items: List[Dict[str, Any]] = [_item_dict(i) for i in (snap.get("inventory", []) or [])]
        prompt = str(snap.get("prompt", "") or "").lower()
        equipped_note: Dict[str, Any] | None = None

        equip_match = EQUIP_RE.search(prompt)
        unequip_match = UNEQUIP_RE.search(prompt)
        if equip_match and not unequip_match:
            wanted = equip_match.group("target").strip().lower()
            wanted = re.sub(r"^(the|my|a|an)\s+", "", wanted).strip()
            target = _pick_equip_target(items, wanted)
            if target is not None:
                # One-weapon slot: mark the pick, stow everything else.
                for item in items:
                    props = item.setdefault("properties", {})
                    if isinstance(props, dict) and props.get("weapon_type"):
                        props["equipped"] = item is target
                target["properties"]["equipped"] = True
                equipped_note = _weapon_stats_note(target)
        elif unequip_match and not equip_match:
            for item in items:
                props = item.get("properties") or {}
                if props.get("weapon_type"):
                    props["equipped"] = False
            equipped_note = {"stowed": [str(i.get("name", "?")) for i in items
                                        if (i.get("properties") or {}).get("weapon_type")]}

        return {"inventory": items,
                "equipped": equipped_note,
                "usage": {"llm_calls": 0, "tokens_est": 0}}
    except Exception as e:
        return {"inventory": [], "error": str(e), "usage": {"llm_calls": 0, "tokens_est": 0}}
