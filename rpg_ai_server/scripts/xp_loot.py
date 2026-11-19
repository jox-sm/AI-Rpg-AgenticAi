from __future__ import annotations

"""XP + loot economy — compatibility facade.

Implementation now lives in `scripts.economy` ({common, xp, loot, difficulty,
awards}); this module re-exports the same objects so every caller keeps working.

XP: kill_xp = round_half_up(xp_base * level * RARITY_XP_MULT * TIER_MULT * TYPE_MULT).
Non-killing attacks grant participation_tick = max(1, kill_xp // 4).
Loot resolves item-db "Loot" strings through ItemsDB, rolled with rarity luck.
Stat scale is the mortal 3..30 range (single digits are baby-tier).
Difficulty is a one-way 1.0x -> 4.0x scalar driven by rarity-weighted kills.
"""

from .economy.common import (
    RARITY_ORDER, RARITY_XP_MULT, RARITY_LUCK, RARITY_ROLL_BONUS,
    TIER_MULT, TIER_ROLLS, TYPE_MULT, STAT_MIN, STAT_MAX,
    round_half_up, clamp_stat, normalize_rarity, normalize_tier, parse_level_range,
)
from .economy.xp import kill_xp, participation_tick, apply_level_ups
from .economy.loot import (
    roll_qty, parse_loot_string, resolve_loot_entry, enemy_db_row, roll_loot, merge_loot,
)
from .economy.difficulty import (
    RARITY_DIFF_WEIGHT, TURNS_PER_DAY, SCALAR_MAX, HEAT_RATE, DAY_RATE, DAY_GRACE,
    ensure_difficulty, advance_day_tracker, difficulty_scalar, difficulty_report,
    add_kill_heat, track_fight,
)
from .economy.awards import award_for_kills
