"""Deterministic infinite world: per-coordinate seeding, border expansion, revisits.

Pure logic only — no LLM, no Redis, no network (ItemsDB is local disk).
"""

import asyncio
import copy

from rpg_ai_server.agents.node0_worldgen import node0_worldgen
from rpg_ai_server.scripts.world_generator import (
    WORLD_INITIAL_SIZE,
    clear_patch,
    ensure_world,
    generate_cell,
    get_world_cell,
    maybe_expand_world,
    move_player,
    parse_move,
    patch_cell,
)


def _run(coro):
    return asyncio.run(coro)


def _content(cell):
    """Generated content without live state (explored is gameplay state, not seed output)."""
    c = dict(cell)
    c.pop("explored", None)
    return c


def test_generate_cell_deterministic_per_coordinate():
    a = generate_cell("seed-1", 10, 20)
    b = generate_cell("seed-1", 10, 20)
    assert a == b
    assert _content(generate_cell("seed-1", 10, 20)) == _content(generate_cell("seed-1", 10, 20))
    # Same seed, same region lattice: neighbours share biome but differ in contents.
    assert generate_cell("seed-1", 3, 3)["biome"] == generate_cell("seed-1", 3, 3)["biome"]


def test_generate_cell_seed_matters():
    diffs = sum(
        1
        for (x, y) in [(0, 0), (5, 9), (-3, 14)]
        if generate_cell("seed-A", x, y) != generate_cell("seed-B", x, y)
    )
    assert diffs >= 1


def test_ensure_world_initial_shape():
    gd: dict = {}
    ensure_world(gd, "sid-1")
    assert gd["world_seed"] == "sid-1"
    assert len(gd["grid"]) == WORLD_INITIAL_SIZE
    assert len(gd["grid"][0]) == WORLD_INITIAL_SIZE
    assert gd["origin"] == {"x": 0, "y": 0}
    assert gd["player_pos"] == {"x": 3, "y": 3, "depth": 0}
    assert gd["grid"][3][3]["explored"] is True
    # Idempotent: second call keeps player + cells.
    snapshot = copy.deepcopy(gd)
    ensure_world(gd, "sid-1")
    assert gd == snapshot


def test_ensure_world_migrates_legacy_grid():
    legacy = {
        "grid": [[{"biome": "Plains", "explored": False} for _ in range(6)] for _ in range(6)],
        "world": {"name": "Old", "seed": "legacy-sid"},
    }
    ensure_world(legacy, "legacy-sid")
    assert legacy["origin"] == {"x": 0, "y": 0}
    assert legacy["player_pos"] == {"x": 3, "y": 3, "depth": 0}
    assert legacy["world_seed"] == "legacy-sid"
    assert legacy["grid"][0][0]["x"] == 0 and legacy["grid"][0][0]["y"] == 0


def test_expansion_at_border_preserves_and_regenerates():
    gd: dict = {}
    ensure_world(gd, "expand-seed")
    before_00 = copy.deepcopy(gd["grid"][0][0])
    gd["player_pos"] = {"x": 0, "y": 0, "depth": 0}
    report = maybe_expand_world(gd)
    assert report["expanded"] is True
    assert "west" in report["directions"] and "north" in report["directions"]
    assert gd["origin"] == {"x": -2, "y": -2}
    # Previously stored cell keeps its (possibly mutated) state object.
    ox, oy = gd["origin"]["x"], gd["origin"]["y"]
    stored_00 = gd["grid"][0 - oy][0 - ox]
    assert _content(stored_00) == _content(before_00)
    # New frontier cell is pure regeneration of its coordinate.
    assert _content(gd["grid"][0][0]) == _content(generate_cell("expand-seed", ox, oy))
    # Center needs no expansion.
    gd["player_pos"] = {"x": 2, "y": 2, "depth": 0}
    report2 = maybe_expand_world(gd)
    assert report2["expanded"] is False


def test_revisit_regenerates_same_place():
    gd: dict = {}
    ensure_world(gd, "revisit-seed")
    frontier = _content(get_world_cell(gd, 50, -40))
    assert frontier == _content(generate_cell("revisit-seed", 50, -40))
    # Walk there: expansions elsewhere must not alter far regeneration.
    move_player(gd, -1, 0, world_seed="revisit-seed")
    assert _content(get_world_cell(gd, 50, -40)) == frontier


def test_negative_coords_and_origin_shift():
    gd: dict = {}
    ensure_world(gd, "neg-seed")
    info = move_player(gd, -3, -3, world_seed="neg-seed")  # (3,3) -> (0,0), triggers expansion
    assert info["moved_to"] == [0, 0]
    assert gd["origin"]["x"] < 0 and gd["origin"]["y"] < 0
    cell = get_world_cell(gd, 0, 0)
    assert cell["x"] == 0 and cell["y"] == 0
    assert cell["explored"] is True


def test_max_size_caps_with_blocked_flag():
    gd: dict = {}
    ensure_world(gd, "cap-seed")
    gd["player_pos"] = {"x": 0, "y": 0, "depth": 0}
    report = maybe_expand_world(gd, max_size=6)
    assert report["expanded"] is False
    assert report["blocked"] is True
    assert len(gd["grid"]) <= 6 and len(gd["grid"][0]) <= 6


def test_parse_move_verbs_and_bare():
    assert parse_move("go north") == (0, -1)
    assert parse_move("Move SOUTH!") == (0, 1)
    assert parse_move("head east") == (1, 0)
    assert parse_move("walk w") == (-1, 0)
    assert parse_move("West") == (-1, 0)
    assert parse_move("attack the goblin") is None
    assert parse_move("snow") is None
    assert parse_move("") is None
    assert parse_move(None) is None


def test_move_marks_explored_and_reports_biome():
    gd: dict = {}
    ensure_world(gd, "move-seed")
    info = move_player(gd, 1, 0, world_seed="move-seed")
    assert info["moved_to"] == [4, 3]
    assert "biome" in info
    assert get_world_cell(gd, 4, 3)["explored"] is True


def test_node0_worldgen_moves_and_expands_without_llm():
    state = {"uuid": "sid-node", "prompt": "go north", "game_data": {}}
    out = _run(node0_worldgen(state))
    assert out["game_data"]["player_pos"] == {"x": 3, "y": 2, "depth": 0}
    assert len(out["grid_data"]["all"]) == WORLD_INITIAL_SIZE * WORLD_INITIAL_SIZE
    assert any("moved to (3,2)" in line for line in out.get("tool_results", []))

    corner = {"uuid": "sid-node", "prompt": "look around", "game_data": out["game_data"]}
    corner["game_data"] = copy.deepcopy(out["game_data"])
    corner["game_data"]["player_pos"] = {"x": 0, "y": 0, "depth": 0}
    out2 = _run(node0_worldgen(corner))
    assert any("expanded" in line for line in out2.get("tool_results", []))
    assert out2["game_data"]["origin"] == {"x": -2, "y": -2}


def test_node0_worldgen_no_move_no_expansion_is_quiet():
    state = {"uuid": "sid-quiet", "prompt": "attack the goblin", "game_data": {}}
    out = _run(node0_worldgen(state))
    assert out["game_data"]["player_pos"] == {"x": 3, "y": 3, "depth": 0}
    assert out.get("tool_results", []) == []


def test_orchestrator_initial_state_carries_world():
    from rpg_ai_server.engine.orchestrator import GameOrchestrator
    from rpg_ai_server.schemas.types import GameRequest

    orch = GameOrchestrator(output_cache=None, game_state_mgr=None, worker_id="w1")
    first = orch._build_initial_state(GameRequest(uuid="sid-det", prompt="hi"))
    second = orch._build_initial_state(GameRequest(uuid="sid-det", prompt="hi"))
    gd = first["game_data"]
    assert gd["world_seed"] == "sid-det"
    assert gd["origin"] == {"x": 0, "y": 0}
    assert gd["player_pos"] == {"x": 3, "y": 3, "depth": 0}
    assert len(first["grid_data"]["all"]) == WORLD_INITIAL_SIZE * WORLD_INITIAL_SIZE
    # Same sid -> same deterministic world across restarts.
    assert first["game_data"]["grid"] == second["game_data"]["grid"]
    # Client-supplied fields survive alongside the world.
    custom = orch._build_initial_state(GameRequest(uuid="sid-c", prompt="hi", data={"quest": "rats"}))
    assert custom["game_data"]["quest"] == "rats"
    assert custom["game_data"]["world_seed"] == "sid-c"


def test_patch_cell_overlay_wins_over_grid():
    gd: dict = {}
    ensure_world(gd, "patch-seed")
    base = get_world_cell(gd, 3, 3)
    patched = patch_cell(gd, 3, 3, {"features": ["crater"], "biome": "Crater"})
    assert patched["features"] == ["crater"]
    assert patched["biome"] == "Crater"
    # Untouched fields survive from the base cell.
    assert patched["difficulty"] == base["difficulty"]
    assert patched["x"] == 3 and patched["y"] == 3
    # Reads return the patch, not the stored grid cell.
    assert get_world_cell(gd, 3, 3)["features"] == ["crater"]
    # Stacking patches merges onto the previous snapshot.
    patch_cell(gd, 3, 3, {"weather": ["Ashen"]})
    assert get_world_cell(gd, 3, 3)["weather"] == ["Ashen"]
    assert get_world_cell(gd, 3, 3)["features"] == ["crater"]


def test_patch_out_of_window_without_expansion():
    gd: dict = {}
    ensure_world(gd, "patch-seed-2")
    size_before = len(gd["grid"])
    patched = patch_cell(gd, 100, -50, {"features": ["watchtower"]})
    assert patched["x"] == 100 and patched["y"] == -50
    assert len(gd["grid"]) == size_before  # no materialization
    assert get_world_cell(gd, 100, -50)["features"] == ["watchtower"]


def test_clear_patch_restores_base():
    gd: dict = {}
    ensure_world(gd, "patch-seed-3")
    patch_cell(gd, 2, 2, {"biome": "Crater"})
    assert clear_patch(gd, 2, 2) is True
    assert clear_patch(gd, 2, 2) is False
    assert get_world_cell(gd, 2, 2)["biome"] != "Crater"


def test_overlay_survives_node0_turn():
    gd: dict = {}
    ensure_world(gd, "patch-seed-4")
    patch_cell(gd, 3, 3, {"features": ["mine"]})
    state = {"uuid": "sid-patch", "prompt": "look around", "game_data": gd}
    out = _run(node0_worldgen(state))
    assert out["game_data"]["cell_patches"]["coord:3:3"]["features"] == ["mine"]
