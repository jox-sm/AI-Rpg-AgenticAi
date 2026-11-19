"""Deterministic OpenRouter-compatible client used by the offline mock chat."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional

from rpg_ai_server.config.settings import settings
from rpg_ai_server.scripts.world_generator import get_world_cell
from rpg_ai_server.utils.logger import logger

from .common import _MONSTERS, _envelope, _seconds, _when_true, MimicOptions

class MimicOpenRouterClient:
    """Deterministic stand-in for the OpenRouter ``chat/completions`` client.

    Graph nodes keep using the real ``get_openrouter_direct()`` factory; we
    only replace the singleton object, so the graph still produces OpenRouter
    shaped responses (exactly what a live key would see).
    """

    def __init__(self, opts: Optional[MimicOptions] = None):
        self.opts = opts or MimicOptions()
        self.calls: List[Dict[str, Any]] = []

    # -- plumbing ---------------------------------------------------------
    def _classify(self, prompt: str) -> Dict[str, Any]:
        low = prompt.lower()
        attack_words = ("slay", "attack", "kill", "hit", "strike", "smite",
                        "fight", "shoot", "stab", "smash", "swing")
        flee_words = ("flee", "run away", "run ", "escape", "retreat", "withdraw",
                      "disengage", "fall back", "leg it")
        trick_words = ("bomb", "explosiv", "smoke", "sand", "pepper", "flour",
                       "decoy", "flash", "oil", "firecracker")
        target = ""
        for name in _MONSTERS:
            if name in low:
                target = name
                break
        if target:
            target = target.title()

        if _when_true(low, attack_words):
            intent = "attack"
            if not target:
                target = ""
        elif _when_true(low, flee_words):
            intent = "flee"
        elif _when_true(low, ("craft", "forge", "make ", "brew ")):
            intent, target = "craft", ""
        elif _when_true(low, ("rest", "sleep", "camp")):
            intent, target = "rest", ""
        elif _when_true(low, ("persuade", "talk", "ask", "greet", "convince")):
            intent, target = "social", ""
        else:
            intent, target = "explore", ""

        need_search = self.opts.use_search and _when_true(
            low, ("lore", "tell", "what is", "history", "legend", "story of"))

        report: Dict[str, Any] = {
            "intent": intent,
            "target": target,
            "flee_method": ("trick" if _when_true(low, trick_words) else ("run" if intent == "flee" else "")),
            "skill_hint": ("acrobatics" if intent == "flee" else ("athletics" if intent == "move" else "")),
            "monster_move": ("attack" if intent == "attack" else "none"),
            "buffs": [], "debuffs": [], "damage_hint": "",
            "needs_search": need_search,
            "needs_image": False,
            "needs_redescribe": False,
            "search_query": (prompt[:120] if need_search else ""),
            "confidence": 0.98,
            "reason": "mimic-openrouter-deterministic",
        }
        return report

    def _jev_trick(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        low = str(payload.get("attempt", "") or "").lower()
        inv = [str(i) for i in (payload.get("inventory") or [])]
        item_bonus = sum(1 for i in inv if any(k in i.lower() for k in ("bomb", "explosiv", "smoke", "flash")))
        base = 0.08 + (0.10 if item_bonus else 0.0)
        if _when_true(low, ("smoke", "flash", "sand", "pepper", "flour")):
            return {"skill": "acrobatics", "stat": "agility", "bonus": min(0.4, base + 0.10),
                    "blind": True, "damage": "1d6" if item_bonus else "0",
                    "reason": "mimic: helpful trick"}
        if _when_true(low, ("explosiv", "bomb", "dynamite", "firecracker")):
            return {"skill": "explosives", "stat": "agility", "bonus": min(0.4, base + 0.15),
                    "blind": True, "damage": "1d6", "reason": "mimic: loud gambit"}
        return {"skill": "acrobatics", "stat": "agility", "bonus": base,
                "blind": False, "damage": "0", "reason": "mimic: plain sprint"}

    def _context(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        gd = payload.get("game_data") or {}
        pos = gd.get("player_pos") or {}
        cell = get_world_cell(gd, pos.get("x", 0), pos.get("y", 0))
        biome = cell.get("biome", "Unknown") if isinstance(cell, dict) else "Unknown"
        return {
            "active_quests": [],
            "current_location": f"({pos.get('x', 0)},{pos.get('y', 0)}) {biome}",
            "party_members": [],
            "recent_events": [],
            "inventory_summary": {},
            "key_items": [],
            "time_of_day": "day",
            "weather": "clear",
            "narrative_context": f"Standing at ({pos.get('x', 0)},{pos.get('y', 0)}) in {biome}.",
        }

    def _images(self, prompt: str, model: str) -> str:
        # Model reuse: image processor/redescriptor can reuse a visual blurb.
        return json.dumps({"blurb": f"A {model.split('/')[-1]} glimpse: {prompt[:120]}"}, ensure_ascii=False)

    def _story(self, prompt: str, call: int) -> str:
        ctx = prompt.split("CONTEXT:", 1)[-1].split("ENVIRONMENT:", 1)[0] if "CONTEXT:" in prompt else prompt
        mech = ""
        if "GAME MECHANICS:" in prompt:
            mech = prompt.split("GAME MECHANICS:", 1)[-1].split("RESPOND WITH", 1)[0].strip()
            mech = mech.split("\nLore Research")[0].strip()
        location = ""
        for line in ctx.splitlines()[:8]:
            if line.startswith("Location:"):
                location = line.split("Location:", 1)[-1].strip()
                break
        action = prompt.strip()
        if "RESPOND WITH" in prompt:
            action = action.split("RESPOND WITH")[0].strip()
        action = action[:200]
        if repo := location:
            prefix = f"You are somewhere near {repo}"
        else:
            prefix = f"You act on {action or 'the world'}"
        story = f"{prefix}. {mech or 'Nothing unusual stirs.'}"
        if self.opts.talkative:
            story += " Somewhere close by, the day continues to unfold."
        if call % 2 == 0:
            story += " You shift carefully, wary of what waits beyond the tree line."
        else:
            story += " You steady your breath and prepare for whatever comes next."
        return story

    async def chat_completion(self, model: str, messages: List[Dict[str, Any]],
                               response_format: Optional[Dict[str, str]] = None,
                               temperature: float = 0.0,
                               max_tokens: int = 4096) -> Dict[str, Any]:
        system = str(messages[0].get("content", "")) if messages else ""
        user = str(messages[1].get("content", "")) if len(messages) > 1 else ""
        try:
            payload = json.loads(user)
        except Exception:
            payload = {}
        prompt = (payload.get("prompt") if isinstance(payload, dict) else user) or user
        call = len(self.calls) + 1
        models = settings.models

        if model == models.classifier_model:
            report = self._classify(prompt)
            content = json.dumps(report, ensure_ascii=False)
            usage_in, usage_out = 220, 60
            tag = f"classifier -> {report['intent']} ({report['target'] or 'world'})"
        elif model == models.context_injector_model:
            content = json.dumps(self._context(payload), ensure_ascii=False)
            usage_in, usage_out = 1200, 120
            tag = "context-injector -> summary"
        elif model == models.story_model:
            content = self._story(prompt, call)
            usage_in, usage_out = 2600, 180
            tag = "story -> text"
        elif model in (models.image_model, models.redescription_model):
            content = self._images(prompt, model)
            usage_in, usage_out = 900, 80
            tag = f"{model.split('/')[-1]} -> image/redescribe"
        elif model == models.jev_model:
            content = json.dumps(self._jev_trick(payload if isinstance(payload, dict) else {"attempt": prompt}), ensure_ascii=False)
            usage_in, usage_out = 700, 70
            tag = "jev -> trick adjudication"
        else:
            # Unknown / future model — behave like a chat echo as a safe fallback.
            content = user[:400]
            usage_in, usage_out = 300, 60
            tag = "unknown model -> echo"

        env = _envelope(content, model, call, usage_in, usage_out)
        self.calls.append({
            "call": call,
            "model": model,
            "tag": tag,
            "latency_ms": round(37.0 + (call % 7) * 3.2, 1),
            "usage": env["usage"],
            "system_preview": system[:80],
            "prompt_preview": user[:160],
            "envelope": env,
        })
        logger.info(f"[mimic-openrouter] #{call} {model} -> {tag}")
        return env

    async def close(self) -> None:
        return None

def install_mimic(opts: MimicOptions) -> MimicOpenRouterClient:
    """Replace the OpenRouter singleton used by the real graph code."""
    import rpg_ai_server.utils.openrouter_client as openrouter_client
    client = MimicOpenRouterClient(opts)
    openrouter_client._openrouter_client = client  # type: ignore[assignment]
    return client
