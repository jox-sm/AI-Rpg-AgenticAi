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

Compatibility facade: the implementation lives in sibling modules; every name
below is the *same* function object as before (tests monkeypatch them in place).
"""
from .common import (
    MAX_ENGAGED, FLEE_TIMEOUT_SECONDS, TRICK_ITEM_KW, BLIND_KW, JEV_SYSTEM,
    _roll_d100, live_hostiles, engage_pack, currently_engaged, skill_level,
    has_trick_item, flee_chance, random,
)
from .tricks import _fallback_trick, adjudicate_trick
from .retaliation import monster_strike
from .resolve import resolve_flee
