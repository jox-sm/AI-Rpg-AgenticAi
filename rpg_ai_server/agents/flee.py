from __future__ import annotations

"""Run away (and away, and away): flee resolution + pack engagement.

- Pack fights: every live hostile sheet can be engaged (cap MAX_ENGAGED).
  Attacking engages the whole hostile pack; fleeing is checked against all of it.
- Flee chance: agility-driven base, -0.15 per unblinded pursuer, fastest-foe
  penalty, +trick bonus. d100 roll, bounded 5%..95%.
- Tricks (sand waves, explosives, decoys): adjudicated by the "jev" model
  slot (free qwen default) mapping fiction -> {skill, stat, bonus, blind,
  damage}; deterministic fallback when the model is unreachable.
- Blind: blinded monsters retaliate at -4 accuracy, don't hinder fleeing,
  tick down when they act.
"""

import random
import re
from typing import Any, Dict, List, Optional, Tuple

from ..utils.coerce import as_dict, entry_level, entry_name, labeled, stat_int, stat_of, to_int

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
    from ..config.settings import settings
    from ..utils.openrouter_client import chat_json
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


def monster_strike(monster: Dict[str, Any], player_ac: int) -> Tuple[Dict[str, Any], int]:
    """One retaliation swing: blinded foes swing wild (-4), then tick down."""
    from ..scripts import combat_system as _cs
    from ..scripts.dice_engine import Dice
    blinded = to_int(monster.get("blinded", 0))
    acc = to_int(monster.get("acc"), 2) - (4 if blinded else 0)
    res = _cs.resolve_attack(
        attacker_attack=to_int(monster.get("atk"), 4),
        attacker_accuracy=acc,
        target_armor_class=player_ac,
        damage_dice=Dice.D6, damage_count=1,
        damage_bonus=to_int(monster.get("dmg_bonus"), 1),
    )
    if blinded:
        monster["blinded"] = blinded - 1
    return res, acc


async def resolve_flee(snap: Dict[str, Any]) -> Dict[str, Any]:
    """Full flee-turn resolution: disengage on success, opportunity strikes on fail."""
    from ..scripts.dice_engine import roll as _roll
    from ..scripts.xp_loot import difficulty_report
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
                from ..scripts.world_generator import get_world_cell
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
    from ..scripts.xp_loot import award_for_kills, track_fight
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
