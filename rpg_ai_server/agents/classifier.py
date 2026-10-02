from __future__ import annotations

import json
from typing import Any, Dict

from ..config.models import get_classifier_model  # noqa: F401 (kept for compat/tests)
from ..config.settings import settings
from ..schemas.state import GameState
from ..utils.logger import logger
from ..utils.openrouter_client import get_openrouter_direct

CLASSIFIER_SYSTEM = """You are a D&D intent classifier. Output strict JSON only:
{"intent":"attack|defend|cast|flee|social|explore|craft|rest","target":"","monster_move":"attack|defend|flee|buff|debuff|none","buffs":[],"debuffs":[],"damage_hint":"","needs_search":false,"needs_image":false,"needs_redescribe":false,"search_query":"","confidence":0.0,"reason":""}
Rules: multi-label allowed via buffs/debuffs. Set needs_search true only for lore/rules outside state. Confidence <0.6 means route to mechanics directly."""

_DETERMINISTIC_LORE_KW = ("dragon", "lich", "beholder", "spell", "rule", "lore", "monster manual", "damage type")
_REDESCRIBE_KW = ("later", "night falls", "time passes", "transform", "morph")


def deterministic_pass(prompt: str, has_images: bool) -> Dict[str, Any] | None:
    p = (prompt or "").lower()
    if has_images:
        return {"needs_image": True, "reason": "images attached (deterministic)"}
    if any(k in p for k in _REDESCRIBE_KW):
        return {"needs_redescribe": True, "reason": "time-change keyword"}
    if any(k in p for k in _DETERMINISTIC_LORE_KW):
        return {"needs_search": True, "search_query": prompt[:120], "reason": "lore keyword"}
    return None


async def classifier_node(state: GameState) -> Dict[str, Any]:
    """Two-stage intent classifier: deterministic fast-path, then OpenRouter LLM.

    Writes DecisionReport + mirrors legacy needs_* flags for the current router.
    All LLM calls via OpenRouter (gemini-2.0 unavailable). Stateless: no shared
    mutable state, safe under concurrent graph runs.
    """
    prompt = state.get("prompt", "") or ""
    has_images = bool(state.get("images"))
    try:
        fast = deterministic_pass(prompt, has_images)
        if fast is not None and not fast.get("needs_search"):
            # Deterministic image/redescribe — no LLM cost
            report = {
                "intent": "explore", "target": "", "monster_move": "none",
                "buffs": [], "debuffs": [], "damage_hint": "",
                "needs_search": False,
                "needs_image": bool(fast.get("needs_image", False)),
                "needs_redescribe": bool(fast.get("needs_redescribe", False)),
                "search_query": "", "confidence": 0.95,
                "reason": fast.get("reason", "deterministic"),
            }
            return {
                "decision_report": report,
                "needs_search": False,
                "needs_image_processing": report["needs_image"],
                "needs_re_description": report["needs_redescribe"],
            }
        # LLM path: direct httpx client (ChatOpenAI breaks under the httpx
        # legacy-TLS monkeypatch required by Upstash — see P14).
        client = get_openrouter_direct()
        raw = await client.chat_completion(
            model=settings.models.classifier_model,
            messages=[
                {"role": "system", "content": CLASSIFIER_SYSTEM},
                {"role": "user", "content": json.dumps({"prompt": prompt[:2000], "has_images": has_images})},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=512,
        )
        content = raw["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
        text = str(content).strip().strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
        try:
            parsed = json.loads(text[text.index("{"): text.rindex("}") + 1])
        except Exception:
            parsed = {}
        report = {
            "intent": str(parsed.get("intent", "explore") or "explore").lower(),
            "target": str(parsed.get("target", "") or ""),
            "monster_move": str(parsed.get("monster_move", "attack" if "attack" in prompt.lower() else "none")),
            "buffs": list(parsed.get("buffs", []) or []),
            "debuffs": list(parsed.get("debuffs", []) or []),
            "damage_hint": str(parsed.get("damage_hint", "") or ""),
            "needs_search": bool(parsed.get("needs_search", bool(fast and fast.get("needs_search")))),
            "needs_image": bool(parsed.get("needs_image", has_images)),
            "needs_redescribe": bool(parsed.get("needs_redescribe", False)),
            "search_query": str(parsed.get("search_query", "") or prompt[:120]),
            "confidence": float(parsed.get("confidence", 0.7) or 0.7),
            "reason": str(parsed.get("reason", "openrouter-llm") or "openrouter-llm"),
        }
        if report["confidence"] < 0.6:
            report["needs_search"] = False  # low confidence → mechanics directly
        return {
            "decision_report": report,
            "needs_search": report["needs_search"],
            "needs_image_processing": report["needs_image"],
            "needs_re_description": report["needs_redescribe"],
        }
    except Exception as e:
        logger.error(f"Classifier failed: {e}")
        return {
            "decision_report": {
                "intent": "explore", "target": "", "monster_move": "none",
                "buffs": [], "debuffs": [], "damage_hint": "",
                "needs_search": False, "needs_image": has_images,
                "needs_redescribe": False, "search_query": "",
                "confidence": 0.0, "reason": f"fallback:{e}",
            },
            "needs_search": False,
            "needs_image_processing": has_images,
            "needs_re_description": False,
        }
