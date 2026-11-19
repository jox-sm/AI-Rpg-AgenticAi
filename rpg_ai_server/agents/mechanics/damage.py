"""Damage sub-node: speed-ordered two-sided combat resolution."""
from __future__ import annotations

from typing import Any, Dict

from ...utils.coerce import as_dict, stat_int, stat_of, to_int
from .common import _ensure_target, _speed_of_agidex, _strikes_for
from .inventory import _equipped_weapon, _weapon_damage

async def _damage_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    """Full turn resolution: speed-based order + multi-attacks, both sides.

    speed = agility + dexterity. Faster side strikes first; each 50% speed
    edge grants +1 strike (cap 4). The monster retaliates — player HP drops.
    Early termination: a dead monster deals no retaliation; a downed player
    makes no further strikes.
    """
    try:
        from ...scripts import combat_system as _cs
        from ...scripts.dice_engine import Dice
        report = snap.get("decision_report", {}) or {}
        if str(report.get("intent", "") or "").lower() == "flee":
            from ..flee import resolve_flee
            return await resolve_flee(snap)
        if str(report.get("intent", "")) not in ("attack", "cast"):
            return {"damage": {"skipped": True}, "usage": {"llm_calls": 0, "tokens_est": 0}}
        from ...scripts.xp_loot import apply_level_ups, kill_xp, participation_tick
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
        from ..flee import engage_pack, monster_strike
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
        from ...scripts.xp_loot import award_for_kills
        from ...scripts.xp_loot import difficulty_report as _diff_report
        from ...scripts.xp_loot import track_fight
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
