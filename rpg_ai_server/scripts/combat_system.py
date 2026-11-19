"""Compatibility facade: combat logic now lives in the combat package.

Re-exports the same objects so existing callers and importers keep working.
"""
from .dice_engine import (
    Dice,
    attack_roll as dice_attack_roll,
    probability_of_success,
    roll,
    roll_total,
    roll_with_advantage,
    roll_with_disadvantage,
    success,
    success_with_bonus,
)
from .combat.common import DAMAGE_TYPE_EFFECTIVENESS, EFFECT_TO_DAMAGE_TYPE, STATUS_EFFECTS
from .combat.damage import (
    _roll_hit_location,
    apply_damage_multipliers,
    calculate_base_damage,
    resistance_modifier,
    resolve_attack,
)
from .combat.defense import resolve_armor, resolve_block, resolve_dodge
from .combat.status import _damage_type_to_effect, apply_status_effect, process_status_effects
from .combat.turn import full_combat_turn
