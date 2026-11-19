"""Adjudicate a flee gambit: jev model mapping + deterministic fallback."""
from __future__ import annotations

from typing import Any, Dict, List

from ...utils.coerce import entry_name, stat_of, to_int
from .common import BLIND_KW, FLEE_TIMEOUT_SECONDS, JEV_SYSTEM, has_trick_item


def _fallback_trick(prompt: str, skill_hint: str, inventory: Any) -> Dict[str, Any]:
    low = str(prompt or "").lower()
    item = has_trick_item(inventory)
    blind = any(k in low for k in BLIND_KW)
    explosive = bool(item and any(k in item.lower() for k in ("bomb", "explosive", "dynamite", "firecracker")))
    bonus = 0.10 + (0.10 if item else 0.0) + (0.05 if blind else 0.0)
    return {"skill": skill_hint or ("explosives" if explosive else "acrobatics"),
            "stat": "agility",
            "bonus": round(min(0.4, bonus), 2),
            "blind": blind,
            "damage": "1d6" if explosive else "0",
            "reason": "offline fallback"}


async def adjudicate_trick(prompt: str, stats: Any, skills: Any, inventory: Any,
                           engaged: List[Dict[str, Any]], biome: str = "") -> Dict[str, Any]:
    """Ask the jev-slot model to map a flee gambit to skill/stat/bonus.

    The model advises; the dice still decide. Any failure (no key, timeout,
    bad JSON) falls back to deterministic rules so turns never hang.
    """
    from ...config.settings import settings
    from ...utils.openrouter_client import chat_json
    try:
        if not settings.models.jev_model:
            raise RuntimeError("no jev model configured")
        parsed = await chat_json(
            model=settings.models.jev_model,
            system=JEV_SYSTEM,
            payload={
                "attempt": str(prompt or "")[:500],
                "stats": {"agility": stat_of(stats, "agility", 10),
                          "dexterity": stat_of(stats, "dexterity", 10),
                          "level": stat_of(stats, "level", 1)},
                "skills": [entry_name(s) for s in (skills or [])][:12],
                "inventory": [entry_name(i) for i in (inventory or [])][:20],
                "pursuers": [{"name": m.get("name"),
                              "speed": to_int(m.get("agility"), 10) + to_int(m.get("dexterity"), 10)}
                             for m in engaged][:4],
                "terrain": str(biome or "")[:60],
            },
            temperature=0.2,
            timeout=FLEE_TIMEOUT_SECONDS,
        )
        stat = str(parsed.get("stat", "agility") or "agility").lower()
        try:
            bonus = max(0.0, min(0.4, float(parsed.get("bonus", 0.0))))
        except (TypeError, ValueError):
            bonus = 0.0
        return {"skill": str(parsed.get("skill", "acrobatics") or "acrobatics")[:40],
                "stat": stat if stat in ("agility", "dexterity", "strength", "intelligence") else "agility",
                "bonus": round(bonus, 2),
                "blind": bool(parsed.get("blind", False)),
                "damage": str(parsed.get("damage", "0") or "0")[:12],
                "reason": str(parsed.get("reason", "") or "")[:120]}
    except Exception:
        return _fallback_trick(prompt, "", inventory)
