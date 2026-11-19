"""Compatibility facade — mechanics fan-out moved into agents/mechanics/.

Public names (and the mutable _SUBNODES registry) are re-exported unchanged so
existing imports and in-place monkeypatches keep working.
"""
from .mechanics.common import (
    _DEFAULT_SPAWN, _MAX_STRIKES, _SPAWN_TABLE, _ensure_target,
    _hydrate_merged_models, _snapshot, _speed_of_agidex, _strikes_for, _table_for,
    _to_model,
)
from .mechanics.damage import _damage_patch
from .mechanics.dice import _dice_patch
from .mechanics.fanout import _ORDER, _SUBNODES, node4_parallel
from .mechanics.inventory import (
    EQUIP_RE, UNEQUIP_RE, _DMG_RE, _equipped_weapon, _inventory_patch,
    _item_dict, _pick_equip_target, _weapon_damage, _weapon_stats_note,
)
from .mechanics.json_patch import _json_patch
from .mechanics.skill import _skill_patch
from .mechanics.stats import _stats_patch

__all__ = [
    "node4_parallel", "_ORDER", "_SUBNODES", "_snapshot", "_table_for",
    "_ensure_target", "_speed_of_agidex", "_strikes_for", "_dice_patch",
    "_damage_patch", "_stats_patch", "_skill_patch", "_inventory_patch",
    "_json_patch", "_item_dict", "_weapon_damage", "_equipped_weapon",
    "_weapon_stats_note", "_pick_equip_target", "EQUIP_RE", "UNEQUIP_RE",
    "_DMG_RE", "_to_model", "_hydrate_merged_models", "_SPAWN_TABLE",
    "_DEFAULT_SPAWN", "_MAX_STRIKES",
]
