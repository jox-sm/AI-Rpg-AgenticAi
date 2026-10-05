"""Full game loop: NEW GAME -> play -> persist -> RESTART -> continue.

End-to-end proof that inventory, world position, and cell patches survive a
process restart through the same save/resume path GameOrchestrator uses in
production (FakeGamesClient stands in for Redis; deterministic systems only,
no LLM calls).
"""

import asyncio
import uuid as uuid_lib
from typing import Any, Dict, List

from rpg_ai_server.agents.node0_worldgen import node0_worldgen
from rpg_ai_server.engine.orchestrator import GameOrchestrator
from rpg_ai_server.redis.game_state import GameStateManager
from rpg_ai_server.redis.output_cache import OutputCache
from rpg_ai_server.schemas.types import GameRequest, InventoryItem
from rpg_ai_server.scripts.world_generator import get_world_cell, patch_cell
from rpg_ai_server.utils.coerce import model_list

from tests.fakes import FakeGamesClient, FakeOutputClient

# Same allowlist the orchestrator uses when resuming a persisted game.
PERSISTED_FIELDS = ("character_stats", "skills", "inventory", "relationships",
                    "game_data", "context", "chat_log", "context_summary", "decision")

SAVE_FIELDS = ["game_data", "story", "character_stats", "inventory", "skills",
               "relationships", "context_summary", "decision", "chat_log", "context"]


def _run(coro):
    return asyncio.run(coro)


def _boot(shared_redis: FakeGamesClient, worker: str):
    """Fresh orchestrator + manager pair (simulates one process boot)."""
    mgr = GameStateManager(shared_redis, memory=None)
    return GameOrchestrator(OutputCache(FakeOutputClient()), mgr, worker_id=worker), mgr


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


async def _save_turn(mgr: GameStateManager, game_id: str, state: Dict[str, Any], story: str):
    """Persist a finished turn — same shape/fields as process_request."""
    await mgr.save_state(game_id, {
        "game_data": _plain(state.get("game_data", {})),
        "story": story,
        "character_stats": _plain(state.get("character_stats")),
        "inventory": model_list(state.get("inventory")),
        "skills": model_list(state.get("skills")),
        "relationships": model_list(state.get("relationships")),
        "context_summary": _plain(state.get("context_summary")),
        "decision": _plain(state.get("decision")),
        "chat_log": _plain(state.get("chat_log")),
        "context": state.get("context", ""),
    }, SAVE_FIELDS)


async def _resume_turn(orch: GameOrchestrator, mgr: GameStateManager,
                       game_id: str, prompt: str) -> Dict[str, Any]:
    """Rebuild turn state from persisted storage — same merge as process_request."""
    persisted = await mgr.load_state(game_id)
    assert persisted, f"no saved state for {game_id}"
    fresh = orch._build_initial_state(GameRequest(uuid=game_id, prompt=prompt))
    for key in PERSISTED_FIELDS:
        if key in persisted:
            fresh[key] = persisted[key]
    log = list(fresh.get("chat_log", []) or [])
    log.append({"role": "user", "text": prompt, "turn": len(log)})
    fresh["chat_log"] = log
    return fresh


def _loot(state: Dict[str, Any], item: InventoryItem):
    """Add loot, stacking quantities like the real loot system."""
    inv: List[Dict[str, Any]] = state.setdefault("inventory", [])
    for entry in inv:
        if entry.get("item_id") == item.item_id:
            entry["quantity"] += item.quantity
            return entry
    entry = item.model_dump(mode="json")
    inv.append(entry)
    return entry


def test_new_game_play_persist_restart_continue():
    redis = FakeGamesClient()  # the shared Redis both "processes" talk to

    # ── SESSION 1: brand-new game ──
    game_id = f"game-{uuid_lib.uuid4().hex[:8]}"
    orch, mgr = _boot(redis, worker="worker-1")
    state = orch._build_initial_state(GameRequest(uuid=game_id, prompt="begin"))
    _run(mgr.save_initial_state(game_id, _plain(state["game_data"]), "",
                                chat_log=_plain(state["chat_log"]),
                                context=state.get("context", "")))
    assert state["game_data"]["player_pos"] == {"x": 3, "y": 3, "depth": 0}

    # Turn 1: head north, loot, dig a tunnel where we stand.
    state["prompt"] = "go north"
    out = _run(node0_worldgen(state))
    state["game_data"] = out["game_data"]
    assert state["game_data"]["player_pos"] == {"x": 3, "y": 2, "depth": 0}
    _loot(state, InventoryItem(item_id="iron-sword", name="Iron Sword",
                               category="weapon", damage=8, weight=3.0))
    _loot(state, InventoryItem(item_id="torch", name="Torch",
                               category="tool", quantity=2, weight=0.5))
    pos = state["game_data"]["player_pos"]
    patch_cell(state["game_data"], pos["x"], pos["y"],
               {"features": ["dug tunnel"], "biome": "Tunnel"})
    _run(_save_turn(mgr, game_id, state, story="north, loot, dig"))
    assert get_world_cell(state["game_data"], 3, 2)["features"] == ["dug tunnel"]

    # ── "RESTART": everything except Redis is thrown away ──
    del orch, mgr
    orch2, mgr2 = _boot(redis, worker="worker-2")

    # ── SESSION 2: reload + verify + continue ──
    state2 = _run(_resume_turn(orch2, mgr2, game_id, "go east"))
    assert state2["game_data"]["player_pos"] == {"x": 3, "y": 2, "depth": 0}
    assert {(i["name"], i["quantity"]) for i in state2["inventory"]} == \
        {("Iron Sword", 1), ("Torch", 2)}
    dug = get_world_cell(state2["game_data"], 3, 2)
    assert dug and dug.get("features") == ["dug tunnel"]

    # Turn 2 (post-restart): head east, loot potions, far regen stays stable.
    out2 = _run(node0_worldgen(state2))
    state2["game_data"] = out2["game_data"]
    assert state2["game_data"]["player_pos"] == {"x": 4, "y": 2, "depth": 0}
    _loot(state2, InventoryItem(item_id="potion", name="Health Potion",
                                category="potion", quantity=3, weight=0.3))
    assert get_world_cell(state2["game_data"], 50, 50) == \
        get_world_cell(state2["game_data"], 50, 50)
    _run(_save_turn(mgr2, game_id, state2, story="east, potions"))

    # Final reload from a third boot proves the whole chain persisted.
    _, mgr3 = _boot(redis, worker="worker-3")
    final = _run(mgr3.load_state(game_id))
    assert final["game_data"]["player_pos"] == {"x": 4, "y": 2, "depth": 0}
    assert {(i["name"], i["quantity"]) for i in final["inventory"]} == \
        {("Iron Sword", 1), ("Torch", 2), ("Health Potion", 3)}
    assert final["game_data"]["cell_patches"]["coord:3:2"]["features"] == ["dug tunnel"]
    assert len(final["chat_log"]) == 2
