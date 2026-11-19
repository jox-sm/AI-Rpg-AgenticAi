"""Run the real game graph against a mimicked "external model API".

CLI front-end moved here from ``scripts/mock_openrouter_chat.py``. The first
line is kept verbatim because ``main`` feeds ``__doc__`` to argparse.
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from rpg_ai_server.scripts.world_generator import get_world_cell
from rpg_ai_server.utils.logger import logger

from . import ROOT
from .client import MimicOptions, install_mimic
from .common import DEFAULT_SID
from .session import MockSession

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
