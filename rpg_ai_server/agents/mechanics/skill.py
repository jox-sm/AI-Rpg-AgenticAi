"""Skill sub-node: tick cooldowns by one (pure, deterministic)."""
from __future__ import annotations

from typing import Any, Dict

async def _skill_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    try:
        skills = snap.get("skills", []) or []
        # Cooldown tick -1 (pure, no I/O)
        ticked = []
        for s in skills:
            if isinstance(s, dict):
                cd = max(0, int(s.get("cooldown", 0)) - 1)
                ticked.append({**s, "cooldown": cd})
            else:
                ticked.append(s)
        return {"skills": ticked, "usage": {"llm_calls": 0, "tokens_est": 0}}
    except Exception as e:
        return {"skills": [], "error": str(e), "usage": {"llm_calls": 0, "tokens_est": 0}}
