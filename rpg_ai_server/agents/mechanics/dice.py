"""Dice sub-node: one skill check driven by the classified intent."""
from __future__ import annotations

from typing import Any, Dict

async def _dice_patch(snap: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from ...scripts.dice_engine import skill_check
        report = snap.get("decision_report", {}) or {}
        intent = str(report.get("intent", "explore"))
        bonus = 2 if intent == "attack" else 0
        res = skill_check(dc=12, bonus=bonus)
        return {"dice": res, "usage": {"llm_calls": 0, "tokens_est": 0}}
    except Exception as e:
        return {"dice": {"error": str(e)}, "usage": {"llm_calls": 0, "tokens_est": 0}}
