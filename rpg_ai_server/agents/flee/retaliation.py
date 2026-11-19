"""Opportunity-strike retaliation by an engaged monster."""
from __future__ import annotations

from typing import Any, Dict, Tuple

from ...utils.coerce import to_int


def monster_strike(monster: Dict[str, Any], player_ac: int) -> Tuple[Dict[str, Any], int]:
    """One retaliation swing: blinded foes swing wild (-4), then tick down."""
    from ...scripts import combat_system as _cs
    from ...scripts.dice_engine import Dice
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
