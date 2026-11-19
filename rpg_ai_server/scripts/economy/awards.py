from __future__ import annotations

"""Sum kill XP, roll loot and apply level-ups in one pass."""

from typing import Any, Dict, List, Tuple

from .loot import roll_loot
from .xp import apply_level_ups, kill_xp


def award_for_kills(slain: List[Dict[str, Any]], new_stats: Dict[str, Any],
                    player_down: bool) -> Tuple[int, list, list]:
    """Summed kill XP + per-corpse loot rolls + level-ups (all skipped when down)."""
    award, loot = 0, []
    if slain and not player_down:
        for foe in slain:
            if not isinstance(foe, dict):
                continue
            award += kill_xp(foe.get("xp_base", 10), foe.get("level", 1),
                             foe.get("rarity", "common"), foe.get("tier", "normal"),
                             foe.get("type", ""))
            try:
                loot.extend(roll_loot(foe))
            except Exception:
                pass
    events = apply_level_ups(new_stats, award) if award > 0 else []
    return award, loot, events
