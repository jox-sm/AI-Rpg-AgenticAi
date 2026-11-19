"""Shared snapshot/target/merge helpers for the mechanics fan-out."""
from __future__ import annotations

import copy
from typing import Any, Dict

from ...schemas.state import GameState
from ...schemas.types import CharacterStats, InventoryItem, Relationship, Skill
from ...utils.coerce import to_int

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
    from ...scripts.xp_loot import (clamp_stat, enemy_db_row, normalize_rarity,
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
    from ...scripts.xp_loot import difficulty_scalar as _scalar
    from ...scripts.xp_loot import round_half_up as _rhu
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
