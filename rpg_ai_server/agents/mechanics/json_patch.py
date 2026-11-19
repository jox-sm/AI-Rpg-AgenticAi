"""JSON sub-node: classify-report notes for the mechanics summary."""
from __future__ import annotations

from typing import Any, Dict

async def _json_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    try:
        report = snap.get("decision_report", {}) or {}
        notes = []
        if report.get("target"):
            notes.append(f"target:{report['target']}")
        if report.get("monster_move"):
            notes.append(f"monster:{report['monster_move']}")
        return {"notes": notes, "usage": {"llm_calls": 0, "tokens_est": 0}}
    except Exception as e:
        return {"notes": [], "error": str(e), "usage": {"llm_calls": 0, "tokens_est": 0}}
