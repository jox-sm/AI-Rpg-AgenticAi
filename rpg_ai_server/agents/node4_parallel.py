from __future__ import annotations

import asyncio
import copy
import re
from typing import Any, Dict, List, Optional

from ..schemas.state import GameState
from ..schemas.types import CharacterStats, InventoryItem, Relationship, Skill
from ..utils.coerce import as_dict, clamp_int, stat_int, stat_of, to_int
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
        "game_data": copy.deepcopy(state.get("game_data") or {}),
    }


# Spawn stats for a named target that has no sheet yet (ambush encounter).
# speed = agility + dexterity (player default 20). Ratio drives turn order +
# multi-attacks: +1 strike per 50% speed edge, capped at 4 per side.
_SPAWN_TABLE = {
    "dragon": {"hp": 150, "ac": 17, "agility": 16, "dexterity": 14, "atk": 12, "acc": 7, "dmg_bonus": 4,
               "rarity": "legendary", "tier": "boss", "xp_base": 150, "type": "Dragon"},
    "giant": {"hp": 120, "ac": 15, "agility": 12, "dexterity": 8, "atk": 10, "acc": 5, "dmg_bonus": 3,
              "rarity": "epic", "tier": "elite", "xp_base": 200, "type": "Giant"},
    "troll": {"hp": 84, "ac": 15, "agility": 12, "dexterity": 8, "atk": 8, "acc": 4, "dmg_bonus": 2,
              "rarity": "rare", "tier": "normal", "xp_base": 30, "type": "Humanoid"},
    "ogre": {"hp": 59, "ac": 11, "agility": 10, "dexterity": 8, "atk": 7, "acc": 3, "dmg_bonus": 2,
             "rarity": "rare", "tier": "normal", "xp_base": 40, "type": "Humanoid"},
    "orc": {"hp": 22, "ac": 13, "agility": 12, "dexterity": 10, "atk": 6, "acc": 3, "dmg_bonus": 2,
            "rarity": "uncommon", "tier": "normal", "xp_base": 15, "type": "Humanoid"},
    "goblin": {"hp": 20, "ac": 12, "agility": 14, "dexterity": 12, "atk": 5, "acc": 3, "dmg_bonus": 1,
               "rarity": "common", "tier": "normal", "xp_base": 10, "type": "Humanoid"},
    "wolf": {"hp": 18, "ac": 13, "agility": 18, "dexterity": 14, "atk": 6, "acc": 4, "dmg_bonus": 1,
             "rarity": "uncommon", "tier": "normal", "xp_base": 12, "type": "Beast"},
    "skeleton": {"hp": 20, "ac": 13, "agility": 10, "dexterity": 10, "atk": 5, "acc": 2, "dmg_bonus": 1,
                 "rarity": "common", "tier": "normal", "xp_base": 8, "type": "Undead"},
    "spider": {"hp": 16, "ac": 14, "agility": 20, "dexterity": 20, "atk": 5, "acc": 5, "dmg_bonus": 2,
               "rarity": "uncommon", "tier": "normal", "xp_base": 14, "type": "Beast"},
    "rat": {"hp": 8, "ac": 10, "agility": 16, "dexterity": 16, "atk": 3, "acc": 3, "dmg_bonus": 0,
            "rarity": "common", "tier": "normal", "xp_base": 5, "type": "Beast"},
}
_DEFAULT_SPAWN = {"hp": 25, "ac": 12, "agility": 10, "dexterity": 10, "atk": 4, "acc": 2, "dmg_bonus": 1,
                  "rarity": "common", "tier": "normal", "xp_base": 10, "type": ""}

_MAX_STRIKES = 4


def _table_for(low_name: str) -> Dict[str, Any]:
    for key, stats in _SPAWN_TABLE.items():
        if key in low_name:
            return stats
    return _DEFAULT_SPAWN


def _ensure_target(game_data: Dict[str, Any], target_name: str,
                   player_level: int = 1) -> tuple[Dict[str, Any], bool]:
    """Find a live monster by name in game_data, else spawn one (ambush).

    Monsters persist in game_data["monsters"] so HP carries across turns.
    Sheets are grounded in the item-db enemy row when one matches (XP base,
    level range, loot, creature type); the spawn table fills the rest.
    Legacy sheets are migrated in place. Stats are normalized to the mortal
    scale (STAT_MIN..STAT_MAX) and level scales HP/attack slightly.
    """
    from ..scripts.xp_loot import (clamp_stat, enemy_db_row, normalize_rarity,
                                   normalize_tier, parse_level_range)
    name = (target_name or "foe").strip()[:60] or "foe"
    monsters = game_data.get("monsters")
    if not isinstance(monsters, list):
        monsters = []
        game_data["monsters"] = monsters
    low = name.lower()
    base = _table_for(low)
    try:
        plevel = max(1, int(player_level))
    except (TypeError, ValueError):
        plevel = 1
    row = enemy_db_row(name)
    if isinstance(row, dict):
        xp_base = to_int(str(row.get("XP", base.get("xp_base", 10))).strip(), to_int(base.get("xp_base"), 10))
        _, hi = parse_level_range(row.get("Level Range", "1"))
        loot, mtype = row.get("Loot", ""), row.get("Type", "")
    else:
        xp_base, hi, loot, mtype = base.get("xp_base", 10), 1, "", base.get("type", "")
    if str(mtype or "").strip().lower() == "boss":
        tier = "boss"
    else:
        tier = base.get("tier", "normal")
    # Spawn at the player's level, capped by the kind's max: low players meet
    # young/small versions, high players meet full-grown ones. Never above hi.
    # The adaptive scalar (1.0x -> 4.0x) then multiplies fresh spawns' level
    # AND stats (existing mid-fight sheets are never re-scaled).
    from ..scripts.xp_loot import difficulty_scalar as _scalar
    from ..scripts.xp_loot import round_half_up as _rhu
    base_level = max(1, min(plevel, max(1, hi)))
    scalar = _scalar(game_data)
    level = min(30, max(1, _rhu(base_level * scalar)))
    for m in monsters:
        if isinstance(m, dict) and str(m.get("name", "")).lower() in (low, low.rstrip("s"), low + "s"):
            for k in ("agility", "dexterity", "atk", "acc", "dmg_bonus", "ac"):
                m.setdefault(k, base[k])
            m["agility"] = clamp_stat(m.get("agility", 10))
            m["dexterity"] = clamp_stat(m.get("dexterity", 10))
            m.setdefault("max_hp", m.get("hp", 25))
            m.setdefault("status", "hostile")
            m.setdefault("level", base_level)
            m.setdefault("rarity", base.get("rarity", "common"))
            m.setdefault("tier", tier)
            m.setdefault("xp_base", xp_base)
            m.setdefault("loot", loot)
            m.setdefault("type", mtype)
            if int(m.get("hp", 0)) > 0:
                return m, False
    hp = _rhu((int(base["hp"]) + (level - 1) * 5) * scalar)
    monster = {"name": name, "hp": hp, "max_hp": hp,
               "ac": base["ac"],
               "agility": clamp_stat(base["agility"]), "dexterity": clamp_stat(base["dexterity"]),
               "atk": max(1, _rhu((int(base["atk"]) + (level - 1) // 2) * scalar)),
               "acc": max(0, _rhu((int(base["acc"]) + (level - 1) // 3) * scalar)),
               "dmg_bonus": max(0, _rhu(int(base["dmg_bonus"]) * scalar)),
               "level": level, "rarity": normalize_rarity(base.get("rarity", "common")),
               "tier": normalize_tier(tier), "xp_base": xp_base,
               "loot": loot, "type": mtype, "scalar": scalar,
               "status": "hostile", "spawned_this_turn": True}
    monsters.append(monster)
    return monster, True


def _speed_of_agidex(agility: Any, dexterity: Any) -> int:
    return max(1, to_int(agility, 10) + to_int(dexterity, 10))


def _strikes_for(fast_speed: int, slow_speed: int) -> int:
    """Total strikes for the faster side: 1 +1 per 50% speed edge, capped."""
    if slow_speed <= 0:
        return _MAX_STRIKES
    extra = int((fast_speed - slow_speed) // (slow_speed * 0.5))
    return max(1, min(_MAX_STRIKES, 1 + extra))


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
    """Full turn resolution: speed-based order + multi-attacks, both sides.

    speed = agility + dexterity. Faster side strikes first; each 50% speed
    edge grants +1 strike (cap 4). The monster retaliates — player HP drops.
    Early termination: a dead monster deals no retaliation; a downed player
    makes no further strikes.
    """
    try:
        from ..scripts import combat_system as _cs
        from ..scripts.dice_engine import Dice
        report = snap.get("decision_report", {}) or {}
        if str(report.get("intent", "") or "").lower() == "flee":
            from .flee import resolve_flee
            return await resolve_flee(snap)
        if str(report.get("intent", "")) not in ("attack", "cast"):
            return {"damage": {"skipped": True}, "usage": {"llm_calls": 0, "tokens_est": 0}}
        from ..scripts.xp_loot import apply_level_ups, kill_xp, participation_tick
        stats = snap.get("character_stats", {}) or {}
        level = stat_int(stats, "level", 1)
        strength = stat_int(stats, "strength", 10)
        pagility = stat_int(stats, "agility", 10)
        pdex = stat_int(stats, "dexterity", 10)
        php = stat_int(stats, "health", 100)
        already_dead = bool(stat_of(stats, "is_dead", False)) or php <= 0
        attack_bonus = 2 + level // 4 + max(0, (strength - 10) // 2)
        player_speed = _speed_of_agidex(pagility, pdex)
        player_ac = 10 + (pdex - 10) // 2

        game_data = snap.get("game_data", {}) or {}
        if not isinstance(game_data, dict):
            game_data = {}
        new_stats: Dict[str, Any] = dict(as_dict(stats) or {"health": php, "level": level})
        if already_dead:
            # Corpses don't fight: persist death, no rolls, no XP, no loot.
            new_stats["health"] = 0
            new_stats["is_dead"] = True
            game_data["player_dead"] = True
            detail = {"target": str(report.get("target", "") or "foe")[:60],
                      "spawned": False, "order": [], "player_strikes": 0,
                      "monster_strikes": 0, "player_speed": player_speed,
                      "monster_speed": 0, "rounds": [], "hp_before": 0,
                      "hp_after": 0, "player_hp_before": 0, "player_hp_after": 0,
                      "player_down": True, "killed": False, "xp_award": 0,
                      "loot": [], "level_events": []}
            return {"damage": detail, "game_data": game_data,
                    "character_stats": new_stats,
                    "usage": {"llm_calls": 0, "tokens_est": 0}}
        target = str(report.get("target", "") or "foe")[:60]
        monster, spawned = _ensure_target(game_data, target, player_level=level)
        hp_before = to_int(monster.get("hp", 0))
        monster_speed = _speed_of_agidex(monster.get("agility", 10), monster.get("dexterity", 10))

        fn = getattr(_cs, "resolve_attack", None)
        if fn is None:
            raise AttributeError("no resolve_attack in combat_system")

        # Player weapon: loot items carry their DB damage string (e.g. '1d4+2')
        # in properties; armed strikes roll that instead of the raw fists.
        weapon = _equipped_weapon(snap.get("inventory"))
        w_sides, w_count, w_bonus = _weapon_damage(
            (weapon or {}).get("properties", {}).get("damage"))

        # Pack fight: attacking engages every live hostile (cap); each engaged
        # monster retaliates with its own speed-driven strikes. Single-monster
        # fights behave exactly as before.
        from .flee import engage_pack, monster_strike
        pack = engage_pack(game_data, monster)
        pack_speeds = {id(m): _speed_of_agidex(m.get("agility", 10), m.get("dexterity", 10))
                       for m in pack}
        fastest = max(pack_speeds.values(), default=monster_speed)

        if player_speed >= fastest:
            order = ("player", "pack")
            p_strikes = _strikes_for(player_speed, fastest)
        else:
            order = ("pack", "player")
            p_strikes = 1
        m_strikes = _strikes_for(monster_speed, player_speed) if monster_speed > player_speed else 1

        def _pack_strikes(m: Dict[str, Any]) -> int:
            spd = pack_speeds.get(id(m), monster_speed)
            return _strikes_for(spd, player_speed) if spd > player_speed else 1

        rounds: list[Dict[str, Any]] = []
        php_before = php

        def _player_phase() -> None:
            nonlocal php
            for _ in range(p_strikes):
                if php <= 0:
                    break
                # Focus the primary; spare strikes cleave into the next live foe.
                foe = next((m for m in pack if to_int(m.get("hp", 0)) > 0), None)
                if foe is None:
                    break
                res = fn(
                    attacker_attack=8, attacker_accuracy=attack_bonus,
                    target_armor_class=to_int(foe.get("ac"), 12),
                    damage_dice=w_sides, damage_count=w_count, damage_bonus=w_bonus,
                )
                dmg = to_int(res.get("damage", 0))
                foe["hp"] = max(0, to_int(foe.get("hp", 0)) - dmg)
                rounds.append({"side": "player", "target": foe.get("name"),
                               "roll": res.get("roll"), "bonus": attack_bonus,
                               "total_hit_roll": res.get("total_hit_roll"),
                               "ac": foe.get("ac"), "hit": bool(res.get("hit")),
                               "critical": bool(res.get("critical")), "damage": dmg,
                               "foe_hp_after": foe["hp"]})

        def _pack_phase() -> None:
            nonlocal php
            for foe in sorted(pack, key=lambda m: pack_speeds.get(id(m), 0), reverse=True):
                if php <= 0:
                    break
                if to_int(foe.get("hp", 0)) <= 0:
                    continue
                for _ in range(_pack_strikes(foe)):
                    if to_int(foe.get("hp", 0)) <= 0 or php <= 0:
                        break
                    res, acc = monster_strike(foe, player_ac)
                    dmg = to_int(res.get("damage", 0))
                    php = max(0, php - dmg)
                    rounds.append({"side": "monster", "by": foe.get("name"),
                                   "target": foe.get("name"),
                                   "roll": res.get("roll"), "bonus": acc,
                                   "total_hit_roll": res.get("total_hit_roll"),
                                   "ac": player_ac, "hit": bool(res.get("hit")),
                                   "critical": bool(res.get("critical")), "damage": dmg,
                                   "player_hp_after": php})

        for side in order:
            if php <= 0:
                break
            if side == "player":
                _player_phase()
            else:
                _pack_phase()
        monster.pop("spawned_this_turn", None)
        killed = to_int(monster.get("hp", 0)) <= 0
        if killed:
            monster["status"] = "dead"
        # Pack members were all alive at turn start: any at 0 now died this turn.
        slain = []
        for foe in pack:
            if to_int(foe.get("hp", 0)) <= 0:
                foe["status"] = "dead"
                foe["engaged"] = False
                slain.append(foe)
        player_down = php <= 0

        # Shared economy: summed kill XP + loot + level-ups, then telemetry.
        from ..scripts.xp_loot import award_for_kills
        from ..scripts.xp_loot import difficulty_report as _diff_report
        from ..scripts.xp_loot import track_fight
        award, loot, level_events = award_for_kills(slain, new_stats, player_down)
        if not award and not player_down:
            award = participation_tick(kill_xp(monster.get("xp_base", 10), monster.get("level", 1),
                                               monster.get("rarity", "common"),
                                               monster.get("tier", "normal"), monster.get("type", "")))
            if award > 0:
                level_events = apply_level_ups(new_stats, award)
        track_fight(game_data, rounds, slain, player_down, already_dead)
        diff_info = _diff_report(game_data)
        new_stats["health"] = php if not level_events else new_stats.get("health", php)
        new_stats["is_dead"] = player_down
        game_data["player_dead"] = player_down

        detail = {
            "target": monster.get("name"),
            "weapon": str((weapon or {}).get("name", "") or "fists"),
            "spawned": spawned,
            "order": list(order),
            "player_strikes": p_strikes,
            "monster_strikes": m_strikes,
            "pack": [str(m.get("name")) for m in pack],
            "pack_strikes": sum(1 for r in rounds if r.get("side") == "monster"),
            "slain": [str(m.get("name")) for m in slain],
            "player_speed": player_speed,
            "monster_speed": monster_speed,
            "rounds": rounds,
            "hp_before": hp_before,
            "hp_after": int(monster.get("hp", 0)),
            "player_hp_before": php_before,
            "player_hp_after": php,
            "player_down": player_down,
            "killed": killed,
            "xp_award": award,
            "xp_total": int(new_stats.get("experience", 0) or 0),
            "player_level": int(new_stats.get("level", level) or level),
            "loot": loot,
            "level_events": level_events,
            "difficulty": diff_info,
        }
        return {"damage": detail, "game_data": game_data,
                "character_stats": new_stats,
                "usage": {"llm_calls": 0, "tokens_est": 0}}
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


def _to_model(model_cls: Any, value: Any) -> Any:
    """Coerce a persisted dict back to its typed model, else pass through."""
    if not isinstance(value, dict):
        return value
    try:
        return model_cls.model_validate(value)
    except Exception:
        return value


def _hydrate_merged_models(merged: Dict[str, Any]) -> None:
    """Restore shade/model keys after the ordered mechanics merge.

    ``character_stats``/``skills``/``inventory`` often arrive as JSON dicts from
    Redis. Persisted turns are dictified; downstream expects models again.
    """
    merged["character_stats"] = _to_model(CharacterStats, merged.get("character_stats"))
    for key, model in (("skills", Skill),
                       ("inventory", InventoryItem),
                       ("relationships", Relationship)):
        if isinstance(merged.get(key), list):
            merged[key] = [_to_model(model, item) for item in merged[key]]



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
        from ..scripts.xp_loot import merge_loot
        merged["inventory"] = merge_loot(merged.get("inventory", state.get("inventory")), loot)
    _hydrate_merged_models(merged)
    return merged
