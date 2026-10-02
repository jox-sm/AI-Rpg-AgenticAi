from __future__ import annotations

import json

from langchain_core.tools import tool

from ....schemas.enums import DamageType
from ....schemas.types import DamageCalculation
from ....scripts.combat_system import DAMAGE_TYPE_EFFECTIVENESS


@tool
async def damage_multiplier(
    base_damage: int,
    damage_type: str,
    monster_type: str,
    position_description: str = "",
    is_trapped: bool = False,
    is_restrained: bool = False,
    is_unconscious: bool = False,
) -> str:
    """Calculate damage multiplier based on damage type, monster composition, and positioning.

    Args:
        base_damage: Base damage before multipliers
        damage_type: Type of damage (fire, cold, lightning, bludgeoning, slashing, piercing, radiant, necrotic, force, psychic, thunder, acid, poison)
        monster_type: Type of monster for elemental effectiveness (ice, plant, earth, metal, undead, fiend, construct, flesh, etc.)
        position_description: How the target is positioned (e.g., 'buried under tree', 'in a hole', 'pinned')
        is_trapped: Whether the target is fully trapped
        is_restrained: Whether the target is restrained
        is_unconscious: Whether the target is unconscious
    """
    dt = damage_type.lower()

    elemental_mult = DAMAGE_TYPE_EFFECTIVENESS.get(dt, {}).get(monster_type.lower(), 1.0)

    position_mult = 1.0
    position_desc = position_description.lower()

    if is_unconscious:
        position_mult *= 2.5
    if is_restrained:
        position_mult *= 1.5
    if is_trapped:
        position_mult *= 2.0

    if "hole" in position_desc or "pit" in position_desc:
        position_mult *= 1.3
    if "burn" in position_desc or "fire" in position_desc:
        position_mult *= 1.2
    if "stuck" in position_desc or "pinned" in position_desc:
        position_mult *= 1.4
    if "buried" in position_desc or "crush" in position_desc:
        position_mult *= 1.6

    total_mult = elemental_mult * position_mult
    total_damage = base_damage * total_mult

    try:
        resolved_damage_type = DamageType(dt)
    except ValueError:
        resolved_damage_type = DamageType.BLUDGEONING

    calc = DamageCalculation(
        base_damage=base_damage,
        damage_type=resolved_damage_type,
        multiplier=total_mult,
        elemental_advantage=elemental_mult,
        position_advantage=position_mult,
        total_damage=round(total_damage, 1),
        description=f"Elemental x{elemental_mult}, Position x{position_mult} = {round(total_damage, 1)} total",
    )
    return json.dumps(calc.model_dump(), indent=2)
