"""Shared flee state, pack engagement and escape-chance helpers."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from ...utils.coerce import entry_level, entry_name, labeled, to_int

MAX_ENGAGED = 4
FLEE_TIMEOUT_SECONDS = 15.0


def _roll_d100() -> int:
    """The escape roll (isolated for tests — combat dice stay truly random)."""
    return random.randint(1, 100)


TRICK_ITEM_KW = ("bomb", "explosive", "dynamite", "firecracker", "smoke",
                 "flash", "oil", "flask", "pepper", "flour", "decoy",
                 "trap", "rope", "grappling", "caltrop", "marble")
BLIND_KW = ("sand", "dust", "flash", "smoke", "pepper", "flour", "blind", "dark")

JEV_SYSTEM = """You are a D&D stunt adjudicator. A player tries to FLEE combat with a gambit.
Given their stats/skills/inventory, the pursuers, and the terrain, output strict JSON only:
{"skill":"acrobatics|athletics|stealth|... or item name","stat":"agility|dexterity|strength|intelligence","bonus":0.0,"blind":false,"damage":"0","reason":"<=20 words"}
Rules: bonus is added flee chance, 0.0 to 0.4. Pure sprints get bonus 0.0. Clever fiction using terrain/items earns up to 0.4. blind true only if foes are plausibly blinded/impaired for ~2 turns (sand, flash, smoke, pepper). damage is dice like "1d6" only if the trick itself wounds (explosives); else "0"."""


def live_hostiles(game_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    mons = game_data.get("monsters")
    if not isinstance(mons, list):
        return []
    return [m for m in mons if isinstance(m, dict)
            and int(m.get("hp", 0) or 0) > 0
            and str(m.get("status", "hostile")) == "hostile"]


def engage_pack(game_data: Dict[str, Any], primary: Optional[Dict[str, Any]] = None,
                cap: int = MAX_ENGAGED) -> List[Dict[str, Any]]:
    """Mark the fighting pack engaged (primary first), cap the mob."""
    pack = live_hostiles(game_data)
    if primary is not None:
        pack = [m for m in pack if m is not primary]
        if isinstance(primary, dict) and int(primary.get("hp", 0) or 0) > 0:
            pack.insert(0, primary)
    engaged = pack[:max(1, cap)]
    for m in game_data.get("monsters") or []:
        if isinstance(m, dict):
            m["engaged"] = m in engaged
    return engaged


def currently_engaged(game_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [m for m in live_hostiles(game_data) if m.get("engaged")]


def skill_level(skills: Any, name: str) -> int:
    """Best matching player skill level by name or type (0 if untrained)."""
    needle = str(name or "").strip().lower()
    if not needle or not isinstance(skills, list):
        return 0
    return max([entry_level(s) for s in skills if needle in labeled(s)] or [0])


def has_trick_item(inventory: Any) -> Optional[str]:
    """First inventory entry whose name smells like a fleeing gadget."""
    if not isinstance(inventory, list):
        return None
    for entry in inventory:
        if any(k in entry_name(entry).lower() for k in TRICK_ITEM_KW):
            return entry_name(entry)
    return None


def flee_chance(agility: Any, dexterity: Any, engaged: List[Dict[str, Any]],
                trick_bonus: float = 0.0) -> float:
    """d100 success chance 0.05..0.95 for outrunning the pack."""
    agi, dex = to_int(agility, 10), to_int(dexterity, 10)
    try:
        bonus = max(0.0, min(0.4, float(trick_bonus)))
    except (TypeError, ValueError):
        bonus = 0.0
    chance = 0.55 + (agi - 10) * 0.04 + (dex - 10) * 0.01 + bonus
    speeds = []
    for m in engaged or []:
        if not to_int((m or {}).get("blinded", 0), 0):
            chance -= 0.15  # unblinded pursuers cut off angles
        speeds.append(to_int((m or {}).get("agility"), 10) + to_int((m or {}).get("dexterity"), 10))
    if speeds:
        chance -= max(0, max(speeds) - (agi + dex)) * 0.01
    return max(0.05, min(0.95, chance))
