from __future__ import annotations

import asyncio
import copy
from typing import Any, Dict

from ..schemas.state import GameState
from ..utils.logger import logger


def _snapshot(state: GameState) -> Dict[str, Any]:
    # Immutable fan-out input: only fields sub-nodes may read (no Redis handles)
    return {
        "uuid": state.get("uuid", ""),
        "turn_id": state.get("turn_id", ""),
        "prompt": state.get("prompt", ""),
        "decision_report": copy.deepcopy(state.get("decision_report") or {}),
        "character_stats": copy.deepcopy(state.get("character_stats") or {}),
        "skills": copy.deepcopy(state.get("skills", []) or []),
        "inventory": copy.deepcopy(state.get("inventory", []) or []),
        "relationships": copy.deepcopy(state.get("relationships", []) or []),
        "grid_data": copy.deepcopy(state.get("grid_data", {}) or {}),
    }


async def _dice_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from ..scripts.dice_engine import skill_check
        report = snap.get("decision_report", {}) or {}
        intent = str(report.get("intent", "explore"))
        bonus = 2 if intent == "attack" else 0
        res = skill_check(dc=12, bonus=bonus)
        return {"dice": res, "usage": {"llm_calls": 0, "tokens_est": 0}}
    except Exception as e:
        return {"dice": {"error": str(e)}, "usage": {"llm_calls": 0, "tokens_est": 0}}


async def _damage_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from ..scripts import combat_system as _cs
        from ..scripts.dice_engine import Dice
        report = snap.get("decision_report", {}) or {}
        if str(report.get("intent", "")) not in ("attack", "cast"):
            return {"damage": {"skipped": True}, "usage": {"llm_calls": 0, "tokens_est": 0}}
        fn = getattr(_cs, "calculate_base_damage", None) or getattr(_cs, "calculate_damage", None)
        if fn is None:
            raise AttributeError("no damage fn in combat_system")
        try:
            dmg = fn(attack=10, defense=10, dice=Dice.D20)
        except TypeError:
            dmg = fn(10, 10)
        return {"damage": {"base": dmg}, "usage": {"llm_calls": 0, "tokens_est": 0}}
    except Exception as e:
        # Fallback pure math (scripts API drift-safe)
        return {"damage": {"base": 5, "fallback": True, "error": str(e)}, "usage": {"llm_calls": 0, "tokens_est": 0}}


async def _stats_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    try:
        stats = snap.get("character_stats", {}) or {}
        level = stats.get("level", 1) if isinstance(stats, dict) else getattr(stats, "level", 1)
        # No auto-heal (fixes stat_tools bug): only report XP tick, merge applies
        return {"stats_delta": {"level": level, "xp_tick": 10}, "usage": {"llm_calls": 0, "tokens_est": 0}}
    except Exception as e:
        return {"stats_delta": {}, "error": str(e), "usage": {"llm_calls": 0, "tokens_est": 0}}


async def _skill_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    try:
        skills = snap.get("skills", []) or []
        # Cooldown tick -1 (pure, no I/O)
        ticked = []
        for s in skills:
            if isinstance(s, dict):
                cd = max(0, int(s.get("cooldown", 0)) - 1)
                ticked.append({**s, "cooldown": cd})
            else:
                ticked.append(s)
        return {"skills": ticked, "usage": {"llm_calls": 0, "tokens_est": 0}}
    except Exception as e:
        return {"skills": [], "error": str(e), "usage": {"llm_calls": 0, "tokens_est": 0}}


async def _inventory_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    try:
        inv = snap.get("inventory", []) or []
        return {"inventory": inv, "usage": {"llm_calls": 0, "tokens_est": 0}}
    except Exception as e:
        return {"inventory": [], "error": str(e), "usage": {"llm_calls": 0, "tokens_est": 0}}


async def _json_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    try:
        report = snap.get("decision_report", {}) or {}
        notes = []
        if report.get("target"):
            notes.append(f"target:{report['target']}")
        if report.get("monster_move"):
            notes.append(f"monster:{report['monster_move']}")
        return {"notes": notes, "usage": {"llm_calls": 0, "tokens_est": 0}}
    except Exception as e:
        return {"notes": [], "error": str(e), "usage": {"llm_calls": 0, "tokens_est": 0}}


_ORDER = ("dice", "damage", "stats", "skill", "inventory", "json")

_SUBNODES = {
    "dice": _dice_patch,
    "damage": _damage_patch,
    "stats": _stats_patch,
    "skill": _skill_patch,
    "inventory": _inventory_patch,
    "json": _json_patch,
}


async def node4_parallel(state: GameState) -> Dict[str, Any]:
    """Atomic parallel mechanics fan-out.

    - Each sub-node gets a deep-copied immutable snapshot (no shared mutable state).
    - No Redis writes here (merge + pusher own persistence).
    - Ordered deterministic merge dice→damage→stats→skill→inventory→json.
    - Idempotent via turn_id: caller dedupes repeat turn_ids.
    """
    turn_id = state.get("turn_id", "")
    logger.info(f"[Node4-parallel] fan-out {_ORDER} turn={turn_id}")
    base = _snapshot(state)
    # One copy per sub-node (no shared refs → no races)
    snaps = {name: copy.deepcopy(base) for name in _ORDER}
    results = await asyncio.gather(
        *(_SUBNODES[name](snaps[name]) for name in _ORDER),
        return_exceptions=True,
    )
    patches: Dict[str, Any] = {}
    for name, res in zip(_ORDER, results):
        if isinstance(res, Exception):
            logger.error(f"[Node4-parallel] {name} crashed: {res}")
            patches[name] = {"error": str(res)}
        else:
            patches[name] = res
    # Ordered merge (single coroutine → deterministic, atomic w.r.t. state update)
    lines = [f"turn={turn_id or '?'} mechanics:"]
    for name in _ORDER:
        p = patches.get(name, {})
        err = p.get("error")
        if err:
            lines.append(f"- {name}: error {err}")
        elif name == "dice" and "dice" in p:
            d = p["dice"]
            lines.append(f"- dice: roll={d.get('roll')} total={d.get('total')} success={d.get('success')}")
        elif name == "damage" and "damage" in p:
            lines.append(f"- damage: {p['damage']}")
        elif name == "stats" and "stats_delta" in p:
            lines.append(f"- stats: {p['stats_delta']}")
        elif name == "skill" and "skills" in p:
            lines.append(f"- skills ticked: {len(p['skills'])}")
        elif name == "inventory":
            lines.append(f"- inventory held: {len(p.get('inventory', []))}")
        elif name == "json" and p.get("notes"):
            lines.append(f"- notes: {', '.join(p['notes'])}")
    summary = "\n".join(lines)
    # Skills/inventory overwrite (not append) — caller replaces, no reducer growth
    merged: Dict[str, Any] = {
        "tool_results": [summary],
        "mechanics_patches": patches,
        "turn_id": turn_id,
    }
    if patches.get("skill", {}).get("skills") is not None:
        merged["skills"] = patches["skill"]["skills"]
    if patches.get("inventory", {}).get("inventory") is not None:
        merged["inventory"] = patches["inventory"]["inventory"]
    return merged
