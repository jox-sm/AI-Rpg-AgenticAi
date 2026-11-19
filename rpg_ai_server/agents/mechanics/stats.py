"""Stats sub-node: report an XP tick; merge applies it."""
from __future__ import annotations

from typing import Any, Dict

async def _stats_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    try:
        stats = snap.get("character_stats", {}) or {}
        level = stats.get("level", 1) if isinstance(stats, dict) else getattr(stats, "level", 1)
        # No auto-heal (fixes stat_tools bug): only report XP tick, merge applies
        return {"stats_delta": {"level": level, "xp_tick": 10}, "usage": {"llm_calls": 0, "tokens_est": 0}}
    except Exception as e:
        return {"stats_delta": {}, "error": str(e), "usage": {"llm_calls": 0, "tokens_est": 0}}
