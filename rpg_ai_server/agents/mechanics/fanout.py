"""Atomic mechanics fan-out: parallel sub-nodes + deterministic ordered merge."""
from __future__ import annotations

import asyncio
import copy
from typing import Any, Dict

from ...schemas.state import GameState
from ...utils.logger import logger
from .common import _hydrate_merged_models, _snapshot
from .dice import _dice_patch
from .damage import _damage_patch
from .stats import _stats_patch
from .skill import _skill_patch
from .inventory import _inventory_patch
from .json_patch import _json_patch

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
        elif name == "damage" and ("damage" in p or "flee" in p):
            if "flee" in p:
                f = p["flee"]
                foes = ", ".join(f.get("escaped") or []) or "no one"
                if not f.get("rounds") and f.get("success") and not f.get("escaped"):
                    lines.append("- flee: nothing chasing you — you slip away")
                elif f.get("success"):
                    blind = " (blinded!)" if f.get("blind_applied") else ""
                    lines.append(
                        f"- flee: {f.get('method', 'run')} ({f.get('skill', '')} "
                        f"+{f.get('bonus', 0.0)}, chance {int(f.get('chance', 0) * 100)}%, "
                        f"rolled {f.get('roll', 0)}){blind} — broke away from {foes}"
                    )
                else:
                    lines.append(
                        f"- flee: CAUGHT (chance {int(f.get('chance', 0) * 100)}%, "
                        f"rolled {f.get('roll', 0)}) — they run you down"
                    )
                for r in f.get("rounds", []) or []:
                    verb = "HIT" if r.get("hit") else "MISS"
                    lines.append(
                        f"- damage: {r.get('target')} strikes you (opportunity): "
                        f"d20={r.get('roll')}+{r.get('bonus')} vs AC{r.get('ac')} {verb}, "
                        f"dmg={r.get('damage')} (your hp ->{r.get('player_hp_after')})"
                    )
                if f.get("killed"):
                    lines.append(f"- damage: your trick KILLED {', '.join(f['killed'])}")
                tail = (f"your hp {f.get('player_hp_before')}->{f.get('player_hp_after')}")
                if f.get("player_down"):
                    tail += " YOU ARE DOWN"
                lines.append(f"- flee: {tail} +{f.get('xp_award', 0)}xp")
                for ev in f.get("level_events", []) or []:
                    lines.append(f"- stats: {ev}")
                loot = f.get("loot", []) or []
                if loot:
                    got = ", ".join(f"+{it.get('quantity', 1)}x {it.get('name', '?')}" for it in loot
                                      if isinstance(it, dict))
                    lines.append(f"- loot: {got}")
                if not f.get("rounds") and f.get("player_down"):
                    lines.append("- flee: you are dead and cannot act")
                continue
            d = p["damage"]
            if isinstance(d, dict) and "rounds" in d:
                spawn = " (ambushed!)" if d.get("spawned") else ""
                order = "->".join(d.get("order", []))
                lines.append(
                    f"- damage: attack {d.get('target')}{spawn} "
                    f"with {d.get('weapon', 'fists')} "
                    f"[order {order}, you x{d.get('player_strikes')} vs foe x{d.get('monster_strikes')}, "
                    f"spd {d.get('player_speed')} vs {d.get('monster_speed')}]"
                )
                for r in d["rounds"]:
                    verb = "HIT" if r.get("hit") else "MISS"
                    crit = " CRIT" if r.get("critical") else ""
                    if r.get("side") == "player":
                        kill = " KILLED" if d.get("killed") else ""
                        lines.append(
                            f"- damage: attack {r.get('target')}: "
                            f"d20={r.get('roll')}+{r.get('bonus')} vs AC{r.get('ac')} {verb}{crit}, "
                            f"dmg={r.get('damage')} (foe hp ->{r.get('foe_hp_after')}){kill}"
                        )
                    else:
                        lines.append(
                            f"- damage: {r.get('target')} strikes you: "
                            f"d20={r.get('roll')}+{r.get('bonus')} vs AC{r.get('ac')} {verb}{crit}, "
                            f"dmg={r.get('damage')} (your hp ->{r.get('player_hp_after')})"
                        )
                tail = (f"foe hp {d.get('hp_before')}->{d.get('hp_after')}, "
                        f"your hp {d.get('player_hp_before')}->{d.get('player_hp_after')}")
                if d.get("player_down"):
                    tail += " YOU ARE DOWN"
                elif d.get("killed"):
                    tail += " KILLED"
                lines.append(f"- damage: {tail} +{d.get('xp_award')}xp "
                             f"(total {d.get('xp_total', 0)}, lvl {d.get('player_level', 1)})")
                for ev in d.get("level_events", []) or []:
                    lines.append(f"- stats: {ev}")
                loot = d.get("loot", []) or []
                if loot:
                    got = ", ".join(f"+{it.get('quantity', 1)}x {it.get('name', '?')}" for it in loot
                                      if isinstance(it, dict))
                    lines.append(f"- loot: {got}")
                diff = d.get("difficulty") or {}
                if diff:
                    lines.append(
                        f"- difficulty: day {diff.get('days', 0)} · {diff.get('kills', 0)} kills · "
                        f"scalar x{diff.get('scalar', 1.0)} "
                        f"(heat {diff.get('heat_pts', 0.0)}pts)"
                    )
                if not d.get("rounds") and d.get("player_down"):
                    lines.append("- damage: you are dead and cannot act")
            elif isinstance(d, dict) and "target" in d:
                verb = "HIT" if d.get("hit") else "MISS"
                crit = " CRIT" if d.get("critical") else ""
                spawn = " (ambushed!)" if d.get("spawned") else ""
                kill = " KILLED" if d.get("killed") else ""
                lines.append(
                    f"- damage: attack {d.get('target')}{spawn}: "
                    f"d20={d.get('roll')}+{d.get('bonus')} vs AC{d.get('ac')} {verb}{crit}, "
                    f"dmg={d.get('damage')} (hp {d.get('hp_before')}->{d.get('hp_after')}){kill} +{d.get('xp_award')}xp"
                )
            else:
                lines.append(f"- damage: {d}")
        elif name == "stats" and "stats_delta" in p:
            lines.append(f"- stats: {p['stats_delta']}")
        elif name == "skill" and "skills" in p:
            lines.append(f"- skills ticked: {len(p['skills'])}")
        elif name == "inventory":
            eq = p.get("equipped") or {}
            kept = len(p.get("inventory", []))
            if eq.get("name"):
                lvl = eq.get("required_level") or 0
                req = f" (requires lvl {lvl})" if lvl else ""
                lines.append(f"- inventory held: {kept} — EQUIPPED {eq.get('name')}: {eq.get('spec', '')}{req}")
            elif "stowed" in eq:
                names = ", ".join(eq.get("stowed") or []) or "nothing"
                lines.append(f"- inventory held: {kept} — stowed {names}")
            else:
                lines.append(f"- inventory held: {kept}")
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
    if isinstance(patches.get("damage", {}).get("game_data"), dict):
        merged["game_data"] = patches["damage"]["game_data"]
    if isinstance(patches.get("damage", {}).get("character_stats"), dict):
        merged["character_stats"] = patches["damage"]["character_stats"]
    # Loot lives one level deeper than the subpatch: inside the damage
    # detail ({..killed/loot..}) for attacks, or inside the flee detail.
    # Reading it from the subpatch itself always yielded [] — kills granted
    # XP/prints but never actually reached the inventory.
    _dmg_sub = patches.get("damage", {}) or {}
    if isinstance(_dmg_sub.get("damage"), dict):
        loot = _dmg_sub["damage"].get("loot") or []
    elif isinstance(_dmg_sub.get("flee"), dict):
        loot = _dmg_sub["flee"].get("loot") or []
    else:
        loot = []
    if loot:
        from ...scripts.xp_loot import merge_loot
        merged["inventory"] = merge_loot(merged.get("inventory", state.get("inventory")), loot)
    _hydrate_merged_models(merged)
    return merged
