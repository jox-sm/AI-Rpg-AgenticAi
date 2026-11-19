"""Run the real game graph against a mimicked "external model API".

Highlights (everything stays in-memory / offline):
- Reuses the project graph v2 (classifier/worldgen/mechanics/story) and the
  real Docker-style mechanics fan-out (dice, combat, loot, world).
- Swaps the OpenRouter HTTP boundary for a deterministic in-memory model that
  returns OpenRouter-shaped envelopes ``{"choices":[{"message":{"content":...}}]}``
  so the graph still exercises the "external LLM API" code path.
- Swaps Upstash Redis / Search for the offline test fakes in ``tests.fakes``.
- Persists session state between fresh Python processes in ``.mock-state/``.

Run:
    python -m rpg_ai_server.utils.mock_chat --boot         # look around once
    python -m rpg_ai_server.utils.mock_chat --listen      # interactive REPL
    python -m rpg_ai_server.utils.mock_chat --say go north --say look around
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Expose the offline test fakes so one script covers Redis/Upstash substitutes.
_TESTS_DIR = ROOT / "tests"
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from tests.fakes import FakeGamesClient, FakeOutputClient  # noqa: E402
from rpg_ai_server.engine import graph_v2 as gv2  # noqa: E402
from rpg_ai_server.engine.orchestrator import GameOrchestrator  # noqa: E402
from rpg_ai_server.redis.game_state import GameStateManager  # noqa: E402
from rpg_ai_server.redis.output_cache import OutputCache  # noqa: E402
from rpg_ai_server.schemas.types import GameRequest  # noqa: E402
from rpg_ai_server.scripts.world_generator import get_world_cell  # noqa: E402
from rpg_ai_server.config.settings import settings  # noqa: E402
from rpg_ai_server.utils.logger import logger  # noqa: E402

STATE_DIR = ROOT / ".mock-state"
DEFAULT_SID = "mock-chat"

_MONSTERS = ("goblin", "dragon", "wolf", "skeleton", "orc", "spider", "troll",
             "ogre", "rat", "bandit", "giant", "bandit leader", "goblin raider")


def _seconds() -> float:
    return time.time()


def _envelope(content: str, model: str, call: int, in_tok: int, out_tok: int) -> Dict[str, Any]:
    return {
        "id": f"chatcmpl-mimic-{call:03}",
        "object": "chat.completion",
        "created": int(_seconds()),
        "model": model,
        "usage": {
            "prompt_tokens": in_tok,
            "completion_tokens": out_tok,
            "total_tokens": in_tok + out_tok,
        },
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
    }


def _when_true(low: str, needles: tuple[str, ...]) -> bool:
    return any(n in low for n in needles)


@dataclass
class MimicOptions:
    """Tunable knobs for the fake OpenRouter-compatible model."""

    use_search: bool = False
    keep_images: bool = False
    talkative: bool = True


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


# ── In-memory Upstash + real graph session ─────────────────────────────

@dataclass
class MockState:
    """Persisted snapshot of Bad_args hashes/counter for one session."""

    hashes: Dict[str, Dict[str, Any]]
    counters: Dict[str, int]
    calls: List[Dict[str, Any]] = dataclasses.field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "MockState":
        if not path.exists():
            return cls(hashes={}, counters={}, calls=[])
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return cls(hashes=raw.get("hashes", {}), counters=raw.get("counters", {}),
                       calls=raw.get("calls", []))
        except Exception:
            return cls(hashes={}, counters={}, calls=[])

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.__dict__, indent=2, default=str), encoding="utf-8")


@dataclass
class MockSession:
    sid: str = DEFAULT_SID
    opts: MimicOptions = dataclasses.field(default_factory=MimicOptions)
    mimic: MimicOpenRouterClient = dataclasses.field(default_factory=MimicOpenRouterClient)
    games: FakeGamesClient = dataclasses.field(default_factory=FakeGamesClient)
    out_client: FakeOutputClient = dataclasses.field(default_factory=FakeOutputClient)
    state_file: Path = dataclasses.field(default_factory=lambda: STATE_DIR / f"{DEFAULT_SID}.json")

    def __post_init__(self) -> None:
        STATE_DIR.mkdir(exist_ok=True)
        self.state_file = STATE_DIR / f"{self.sid}.json"
        self._load()
        self.orch = self._orchestrator()
        self.mimic.calls = self.state.calls

    def _load(self) -> None:
        self.state = MockState.load(self.state_file)
        for sid, fields in self.state.hashes.items():
            self.games.hashes[sid] = dict(fields)
        self.games.counters.update(self.state.counters)

    def _orchestrator(self) -> GameOrchestrator:
        """Fresh orchestrator + compiled graph bound to the fake backends."""
        cache = OutputCache(self.out_client)
        manager = GameStateManager(self.games, memory=None)  # no Upstash Search
        orch = GameOrchestrator(cache, manager, worker_id=f"mimic-{self.sid}")
        orch.compiled_graph = gv2.build_game_graph_v2(cache).compile()
        return orch

    def flush(self) -> None:
        sid = self.sid
        self.state = MockState(
            hashes=self.games.hashes,
            counters=self.games.counters,
            calls=self.mimic.calls,
        )
        self.state.save(self.state_file)

    # -- actions -----------------------------------------------------------
    async def act(self, prompt: str) -> Dict[str, Any]:
        request = GameRequest(uuid=self.sid, prompt=prompt)
        try:
            out = await self.orch.process_request(request)
        finally:
            self.flush()
        if out is None:
            out = {"uuid": self.sid, "error": "no output produced"}
        return out

    async def boot(self) -> Dict[str, Any]:
        out = await self.act("You open your eyes in an unfamiliar world.")
        return out

    async def reset(self) -> Dict[str, Any]:
        self.games.hashes.pop(self.sid, None)
        self.games.counters.pop(self.sid, None)
        self.flush()
        self.orch = self._orchestrator()
        return await self.boot()

    def describe_state(self) -> Dict[str, Any]:
        sid = self.sid
        saved = self.games.hashes.get(sid)
        counter = self.games.counters.get(sid, 0)
        if not saved:
            return {"session": self.sid, "counter": counter, "state": "empty (boot first)"}
        try:
            fields = {k: json.loads(v) for k, v in saved.items()}
        except Exception:
            fields = dict(saved)
        gd = fields.get("game_data") or {}
        cs = gd.get("character_stats") or fields.get("character_stats") or {}
        pos = gd.get("player_pos") or {}
        return {
            "session": self.sid,
            "counter": counter,
            "story": fields.get("story") or "",
            "player_pos": pos,
            "health": cs.get("health"),
            "level": cs.get("level"),
            "xp": cs.get("experience"),
            "monsters": gd.get("monsters") or [],
            "biome": ((get_world_cell(gd, pos.get("x", 0), pos.get("y", 0)) or {}).get("biome") if gd and pos else None),
        }


# ── CLI ────────────────────────────────────────────────────────────────

def _print_story(out: Dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    story = out.get("story") or (out.get("game_data") or {}).get("story") or ""
    if story:
        print("STORY")
        print("-" * 78)
        print(story)
    tools = out.get("tool_results") or []
    if tools:
        print("\nMECHANICS")
        print("-" * 78)
        for t in tools:
            print(f"- {t}")
    gd = out.get("game_data") or {}
    stats = gd.get("character_stats") or {}
    pos = gd.get("player_pos") or {}
    if pos or stats:
        print("\nSTATE")
        print("-" * 78)
        if pos:
            cell = get_world_cell(gd, pos.get("x", 0), pos.get("y", 0))
            biome = cell.get("biome", "unknown") if isinstance(cell, dict) else "unknown"
            print(f"- position: ({pos.get('x')},{pos.get('y')}) depth {pos.get('depth', 0)} · {biome}")
        if stats:
            print(f"- health: {stats.get('health','?')}/{stats.get('max_health','?')} "
                  f"mana {stats.get('mana','?')}/{stats.get('max_mana','?')} "
                  f"xp {stats.get('experience',0)}/{stats.get('experience_to_next',100)}")
        if gd.get("monsters"):
            alive = [m for m in gd["monsters"] if m.get("hp", 0) > 0]
            print(f"- hostiles: {len(alive)} " + ", ".join(
                f"{m['name']} {m.get('hp')}hp" for m in alive[:5]))
    if out.get("game_over"):
        print("\n** YOU ARE DEAD — state saved. Run `--new` to start over. **")
    print("=" * 78 + "\n")


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _repl(session: MockSession) -> int:
    print("\n[mock-openrouter] session ready. Type an action, or 'quit' to exit.")
    print("  (examples: go north | look around | slay the goblin | tell me about dragons).")
    while True:
        try:
            raw = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        if raw in ("quit", "exit", "/quit", "/exit"):
            break
        if raw.startswith("/new"):
            out = _run(session.reset())
            _print_story(out)
            continue
        if raw.startswith("/show"):
            print(json.dumps(session.describe_state(), indent=2, default=str))
            continue
        prompt = raw
        if prompt.startswith("/"):
            prompt = prompt[1:]
        out = _run(session.act(prompt))
        _print_story(out)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.partition("\n")[0])
    parser.add_argument("--sid", default=DEFAULT_SID, help="session id")
    parser.add_argument("--boot", action="store_true", help="start fresh by looking around")
    parser.add_argument("--new", action="store_true", help="wipe session and boot")
    parser.add_argument("--say", action="append", default=[], help="player action (repeatable)")
    parser.add_argument("--listen", action="store_true", help="interactive REPL")
    parser.add_argument("--show", action="store_true", help="print current state summary")
    parser.add_argument("--api-calls", action="store_true", help="after the run, print all meta-envelopes")
    parser.add_argument("--use-search", action="store_true", help="classifier may ask for worldgen search")
    parser.add_argument("--keep-images", action="store_true", help="classifier may process attached images")
    parser.add_argument("--sid-file", help="optional alternate state file path (json)")
    parser.add_argument("--quiet", action="store_true", help="set log level WARNING")
    args = parser.parse_args(argv)
    if args.quiet:
        logger.setLevel("WARNING")

    opts = MimicOptions(use_search=args.use_search, keep_images=args.keep_images)
    session = MockSession(sid=args.sid, opts=opts)
    install_mimic(opts)
    if args.sid_file:
        session.state_file = ROOT / args.sid_file
        session._load()  # reload with user path

    out: Dict[str, Any] = {"session": session.sid, "counter": session.games.counters.get(session.sid, 0)}
    if args.new:
        out = _run(session.reset())
        _print_story(out)
    elif args.boot:
        if not session.games.hashes.get(session.sid):
            out = _run(session.boot())
            _print_story(out)
    elif args.say:
        for prompt in args.say:
            out = _run(session.act(prompt))
            _print_story(out)
    elif args.show:
        print(json.dumps(session.describe_state(), indent=2, default=str))
    elif args.listen or sys.stdin.isatty():
        if not session.games.hashes.get(session.sid):
            out = _run(session.boot())
            _print_story(out)
        return _repl(session)

    if args.api_calls:
        calls = session.mimic.calls
        print(f"\n[mock-openrouter] {len(calls)} mimicked API call(s).")
        for c in calls[-10:]:
            print(json.dumps(c["envelope"], indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
