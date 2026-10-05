from __future__ import annotations

import re
from typing import Any, Dict

from ..config.settings import settings
from ..schemas.state import GameState
from ..utils.logger import logger
from ..utils.openrouter_client import chat_json

CLASSIFIER_SYSTEM = """You are a D&D intent classifier. Output strict JSON only:
{"intent":"attack|defend|cast|flee|social|explore|craft|rest","target":"","flee_method":"","skill_hint":"","monster_move":"attack|defend|flee|buff|debuff|none","buffs":[],"debuffs":[],"damage_hint":"","needs_search":false,"needs_image":false,"needs_redescribe":false,"search_query":"","confidence":0.0,"reason":""}
Rules: multi-label allowed via buffs/debuffs. Set needs_search true only for lore/rules outside state. Confidence <0.6 means route to mechanics directly.
Flee rules: intent "flee" for running away, retreating, escaping. Set flee_method to "run" for a plain sprint or "trick" when the player uses items, terrain, or deception (explosives, sand, smoke, decoys, acrobatics). Set skill_hint to the most relevant skill or item name (acrobatics, athletics, stealth, sleight of hand, survival, explosives, ...), empty if none fits."""

_DETERMINISTIC_LORE_KW = ("dragon", "lich", "beholder", "spell", "rule", "lore", "monster manual", "damage type")
_REDESCRIBE_KW = ("later", "night falls", "time passes", "transform", "morph")
# Explicit combat verbs → zero-LLM attack intent (immune to empty-LLM flakes).
# NOTE: "slay" deliberately excluded (stays on LLM path — covered by tests).
_ATTACK_VERBS = ("attack", "swing", "strike", "stab", "slash", "shoot", "fire at", "cast", "hit", "kill")
_TARGET_STOP = (" with ", " using ", " and ", " then ", " while ")


def _extract_target(prompt: str) -> str:
    low = (prompt or "").lower()
    for verb in sorted(_ATTACK_VERBS, key=len, reverse=True):  # "fire at" before "fire"
        i = low.find(verb)
        if i < 0:
            continue
        tail = (prompt or "")[i + len(verb):].strip(" ,.!?;:")
        for stop in _TARGET_STOP:
            j = tail.lower().find(stop)
            if j >= 0:
                tail = tail[:j]
        # "cast fireball at goblin" → the creature is after the last " at "
        if " at " in tail.lower():
            tail = re.split(r"\s+at\s+", tail, flags=re.IGNORECASE)[-1]
        tail = tail.strip(" ,.!?;:")
        for art in ("the ", "a ", "an ", "that ", "this ", "those ", "these "):
            if tail.lower().startswith(art):
                tail = tail[len(art):]
                break
        tail = tail.strip(" ,.!?;:")
        if tail:
            return tail[:60]
    return "foe"


_ATTACK_RE = re.compile(r"\b(attack|swing|strike|stab|slash|shoot|fire at|cast|hit|kill)\b")

_FLEE_VERBS = ("flee", "run away", "run", "escape", "retreat", "withdraw", "bolt",
               "disengage", "fall back", "get away", "back off", "leg it")
_FLEE_RE = re.compile(r"\b(flee|escape|retreat|withdraw|disengage|run away|fall back|get away|back off|leg it|bolt)\b|\brun\b")
_TRICK_KW = ("explosive", "bomb", "dynamite", "sand", "dust", "smoke", "flash", "blind",
             "distract", "decoy", "trick", "throw", "firecracker", "oil", "flour", "pepper")


def _extract_flee_method(prompt: str) -> str:
    return "trick" if any(k in (prompt or "").lower() for k in _TRICK_KW) else "run"


def deterministic_pass(prompt: str, has_images: bool) -> Dict[str, Any] | None:
    p = (prompt or "").lower()
    if has_images:
        return {"needs_image": True, "reason": "images attached (deterministic)"}
    if _ATTACK_RE.search(p):
        return {
            "intent": "attack",
            "target": _extract_target(prompt or ""),
            "monster_move": "defend",
            "needs_search": False,
            "reason": "attack keyword",
        }
    if _FLEE_RE.search(p):
        return {
            "intent": "flee",
            "flee_method": _extract_flee_method(prompt or ""),
            "skill_hint": "",
            "monster_move": "attack",
            "needs_search": False,
            "reason": "flee keyword",
        }
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
            # Deterministic image/redescribe/attack/flee — no LLM cost
            is_attack = fast.get("intent") == "attack"
            is_flee = fast.get("intent") == "flee"
            report = {
                "intent": "attack" if is_attack else ("flee" if is_flee else "explore"),
                "target": str(fast.get("target", "") or "") if is_attack else "",
                "flee_method": str(fast.get("flee_method", "") or "") if is_flee else "",
                "skill_hint": str(fast.get("skill_hint", "") or ""),
                "monster_move": str(fast.get("monster_move", "defend") or "defend") if (is_attack or is_flee) else "none",
                "buffs": [], "debuffs": [], "damage_hint": "",
                "needs_search": False,
                "needs_image": bool(fast.get("needs_image", False)),
                "needs_redescribe": bool(fast.get("needs_redescribe", False)),
                "search_query": "", "confidence": 0.9 if is_attack else 0.95,
                "reason": fast.get("reason", "deterministic"),
            }
            return {
                "decision_report": report,
                "needs_search": False,
                "needs_image_processing": report["needs_image"],
                "needs_re_description": report["needs_redescribe"],
            }
        # LLM path (ChatOpenAI breaks under the httpx legacy-TLS monkeypatch
        # required by Upstash — direct HTTP only). Failures fall through to
        # the safe-defaults fallback below.
        parsed = await chat_json(
            model=settings.models.classifier_model,
            system=CLASSIFIER_SYSTEM,
            payload={"prompt": prompt[:2000], "has_images": has_images},
            temperature=0.0,
            timeout=60.0,
        )
        report = {
            "intent": str(parsed.get("intent", "explore") or "explore").lower(),
            "target": str(parsed.get("target", "") or ""),
            "flee_method": str(parsed.get("flee_method", "") or "").lower(),
            "skill_hint": str(parsed.get("skill_hint", "") or ""),
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
                "intent": "explore", "target": "", "flee_method": "", "skill_hint": "",
                "monster_move": "none",
                "buffs": [], "debuffs": [], "damage_hint": "",
                "needs_search": False, "needs_image": has_images,
                "needs_redescribe": False, "search_query": "",
                "confidence": 0.0, "reason": f"fallback:{e}",
            },
            "needs_search": False,
            "needs_image_processing": has_images,
            "needs_re_description": False,
        }
