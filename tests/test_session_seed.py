"""Session-seeding contract (turn 1): client `data` is preserved into
game_data, drives world identity, and supplies the campaign payload.

Contract: REDIS_API.md → "Session Seeding from a Catalog Game".
"""

from rpg_ai_server.engine.orchestrator import GameOrchestrator
from rpg_ai_server.redis.game_state import GameStateManager
from rpg_ai_server.redis.output_cache import OutputCache
from rpg_ai_server.schemas.types import GameRequest

from tests.fakes import FakeGamesClient, FakeOutputClient


def _boot() -> GameOrchestrator:
    return GameOrchestrator(
        OutputCache(FakeOutputClient()),
        GameStateManager(FakeGamesClient(), memory=None),
        worker_id="w-test",
    )


def test_turn1_preserves_campaign_and_respects_client_seed():
    orch = _boot()
    campaign = {
        "name": "Sunken Vault",
        "description": "A drowned archive beneath the keep.",
        "characters": [{"id": "c1", "name": "The Mage"}],
        "maps": [{"id": "m1", "name": "Vault Level 1", "places_at": "Great Hall"}],
        "items": [{"id": "i1", "name": "Rusty Key"}],
    }
    state = orch._build_initial_state(
        GameRequest(
            uuid="sid-1",
            prompt="look around",
            data={"turn": 1, "world_seed": "catalog-game-42", "campaign": campaign},
        )
    )
    # Client seed wins over the session id → catalog game shares one world.
    assert state["game_data"]["world_seed"] == "catalog-game-42"
    # Turn-1 data is preserved verbatim into game_data (allowlist merge).
    assert state["game_data"]["campaign"] == campaign
    # The world itself is materialized for the seeded game.
    grid = state["game_data"].get("grid")
    assert isinstance(grid, list) and grid


def test_same_game_seed_same_world():
    orch = _boot()
    a = orch._build_initial_state(
        GameRequest(uuid="sid-1", prompt="hi", data={"world_seed": "game-x"})
    )
    b = orch._build_initial_state(
        GameRequest(uuid="sid-2", prompt="hi", data={"world_seed": "game-x"})
    )
    assert a["game_data"]["grid"] == b["game_data"]["grid"]


def test_plain_scenario_seeds_from_sid():
    orch = _boot()
    s1 = orch._build_initial_state(GameRequest(uuid="sid-a", prompt="hi"))
    s2 = orch._build_initial_state(GameRequest(uuid="sid-b", prompt="hi"))
    assert s1["game_data"]["world_seed"] == "sid-a"
    assert s2["game_data"]["world_seed"] == "sid-b"
    assert s1["game_data"]["grid"] != s2["game_data"]["grid"]
