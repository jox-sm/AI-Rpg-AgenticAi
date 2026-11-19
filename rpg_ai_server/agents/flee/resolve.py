"""Full flee-turn resolution: escape check, retaliation and trick chip damage."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from ...utils.coerce import as_dict, stat_int, stat_of, to_int
from .common import currently_engaged, engage_pack, flee_chance, skill_level
from .retaliation import monster_strike
from .tricks import _fallback_trick


async def resolve_flee(snap: Dict[str, Any]) -> Dict[str, Any]:
    """Full flee-turn resolution: disengage on success, opportunity strikes on fail."""
    # Resolve the two test-patched names through the facade package so the
    # monkeypatches on ``agents.flee`` keep taking effect after the split.
    from . import _roll_d100, adjudicate_trick
    from ...scripts.dice_engine import roll as _roll
    from ...scripts.xp_loot import difficulty_report
    report = snap.get("decision_report", {}) or {}
    stats = snap.get("character_stats", {}) or {}
    game_data = snap.get("game_data", {}) or {}
    if not isinstance(game_data, dict):
        game_data = {}
    prompt = str(snap.get("prompt", "") or "")
    agi = stat_int(stats, "agility", 10)
    dex = stat_int(stats, "dexterity", 10)
    php = stat_int(stats, "health", 100)
    already_dead = bool(stat_of(stats, "is_dead", False)) or php <= 0

    new_stats: Dict[str, Any] = as_dict(stats) or {"health": php}
    if not isinstance(new_stats, dict):
        new_stats = {"health": php}
    else:
        new_stats = dict(new_stats)
    if already_dead:
        new_stats["health"] = 0
        new_stats["is_dead"] = True
        game_data["player_dead"] = True
        detail = {"method": "run", "skill": "", "success": False, "chance": 0.0,
                  "roll": 0, "bonus": 0.0, "blind_applied": False, "escaped": [],
                  "rounds": [], "xp_award": 0, "loot": [], "level_events": [],
                  "killed": [], "player_hp_before": 0, "player_hp_after": 0,
                  "player_down": True, "difficulty": difficulty_report(game_data)}
        return {"flee": detail, "game_data": game_data,
                "character_stats": new_stats, "usage": {"llm_calls": 0, "tokens_est": 0}}

    engaged = currently_engaged(game_data) or engage_pack(game_data)
    method = str(report.get("flee_method", "") or "run").lower()
    if method not in ("run", "trick"):
        low = prompt.lower()
        method = "trick" if any(k in low for k in
                                ("explosive", "bomb", "sand", "smoke", "blind", "trick",
                                 "throw", "distract", "decoy", "flash", "dust")) else "run"

    skill = ""
    trick_bonus = 0.0
    blind = False
    chip_dice = "0"
    if method == "trick":
        try:
            pos = (game_data.get("player_pos") or {})
            biome = ""
            try:
                from ...scripts.world_generator import get_world_cell
                cell = get_world_cell(game_data, pos.get("x", 0), pos.get("y", 0))
                biome = cell.get("biome", "") if isinstance(cell, dict) else ""
            except Exception:
                biome = ""
            trick = await adjudicate_trick(prompt, stats, snap.get("skills"),
                                           snap.get("inventory"), engaged, biome)
        except Exception:
            trick = _fallback_trick(prompt, str(report.get("skill_hint", "") or ""),
                                    snap.get("inventory"))
        skill = trick.get("skill", "")
        try:
            trick_bonus = max(0.0, min(0.4, float(trick.get("bonus", 0.0))))
        except (TypeError, ValueError):
            trick_bonus = 0.0
        trick_bonus += min(0.1, 0.02 * skill_level(snap.get("skills"), skill))
        blind = bool(trick.get("blind", False))
        chip_dice = str(trick.get("damage", "0") or "0")
        if blind:
            for m in engaged:
                m["blinded"] = 2

    chance = flee_chance(agi, dex, engaged, trick_bonus) if engaged else 1.0
    roll = _roll_d100()
    success = (not engaged) or (roll / 100.0) <= chance
    player_ac = 10 + (dex - 10) // 2

    rounds: List[Dict[str, Any]] = []
    killed: List[str] = []
    php_before = php
    if success:
        for m in engaged:
            m["engaged"] = False
    elif engaged:
        # Caught: every pursuer lands one opportunity strike as you turn.
        for m in engaged:
            if php <= 0:
                break
            res, acc = monster_strike(m, player_ac)
            dmg = to_int(res.get("damage", 0))
            php = max(0, php - dmg)
            rounds.append({"side": "monster", "by": m.get("name"), "target": m.get("name"),
                           "roll": res.get("roll"), "bonus": acc,
                           "total_hit_roll": res.get("total_hit_roll"), "ac": player_ac,
                           "hit": bool(res.get("hit")), "critical": bool(res.get("critical")),
                           "damage": dmg, "player_hp_after": php, "opportunity": True})
    # Explosive tricks wound even on the way out.
    if chip_dice.strip() not in ("0", ""):
        m = re.match(r"^\s*(\d+)\s*d\s*(\d+)\s*(?:\+\s*(\d+))?\s*$", chip_dice)
        if m:
            n, sides, plus = min(int(m.group(1)), 6), min(int(m.group(2)), 12), int(m.group(3) or 0)
            for foe in list(engaged):
                if php <= 0:
                    break
                if int(foe.get("hp", 0) or 0) <= 0:
                    continue
                dmg = max(0, sum(_roll(sides, n)) + plus)
                foe["hp"] = max(0, int(foe.get("hp", 0)) - dmg)
                if int(foe.get("hp", 0)) <= 0:
                    foe["status"] = "dead"
                    foe["engaged"] = False
                    killed.append(str(foe.get("name", "?")))
    player_down = php <= 0

    slain = [m for m in engaged if str(m.get("name", "?")) in killed]
    from ...scripts.xp_loot import award_for_kills, track_fight
    award, loot, level_events = award_for_kills(slain, new_stats, player_down)
    new_stats["health"] = php if not level_events else new_stats.get("health", php)
    new_stats["is_dead"] = bool(new_stats.get("is_dead", False)) or player_down
    game_data["player_dead"] = new_stats["is_dead"]
    track_fight(game_data, rounds, slain, player_down, already_dead)

    detail = {"method": method, "skill": skill, "success": bool(success),
              "chance": round(chance, 2), "roll": roll, "bonus": round(trick_bonus, 2),
              "blind_applied": blind, "escaped": [str(m.get("name")) for m in engaged] if success else [],
              "rounds": rounds, "xp_award": award, "xp_total": int(new_stats.get("experience", 0) or 0),
              "loot": loot, "level_events": level_events, "killed": killed,
              "player_hp_before": php_before, "player_hp_after": php,
              "player_down": player_down, "difficulty": difficulty_report(game_data)}
    return {"flee": detail, "game_data": game_data,
            "character_stats": new_stats, "usage": {"llm_calls": 1 if method == "trick" else 0, "tokens_est": 0}}
