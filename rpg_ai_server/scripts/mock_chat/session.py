"""In-memory / on-disk state and the graph session for the offline mock chat."""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from rpg_ai_server.engine import graph_v2 as gv2
from rpg_ai_server.engine.orchestrator import GameOrchestrator
from rpg_ai_server.redis.game_state import GameStateManager
from rpg_ai_server.redis.output_cache import OutputCache
from rpg_ai_server.schemas.types import GameRequest
from rpg_ai_server.scripts.world_generator import get_world_cell
from tests.fakes import FakeGamesClient, FakeOutputClient

from .client import MimicOpenRouterClient
from .common import DEFAULT_SID, MimicOptions, STATE_DIR

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
