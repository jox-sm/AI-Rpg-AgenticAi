"""Adaptive difficulty scalar: 1.0x -> 4.0x max, hard to raise.

One scalar drives both the worldgen density signal (more monsters per cell)
and the combat level/stat multiplier. Slow by design: ~150 common kills AND
two months survived to approach the cap.
"""

import asyncio

from rpg_ai_server.agents.node0_worldgen import node0_worldgen
from rpg_ai_server.agents.node4_parallel import _damage_patch, _ensure_target
from rpg_ai_server.scripts.world_generator import generate_cell
from rpg_ai_server.scripts.xp_loot import (
    RARITY_DIFF_WEIGHT,
    SCALAR_MAX,
    add_kill_heat,
    advance_day_tracker,
    difficulty_report,
    difficulty_scalar,
    ensure_difficulty,
)


def _run(coro):
    return asyncio.run(coro)


def _gd(**kw):
    gd = {"difficulty": {"turns": 0, "days": 0, "kills": 0, "deaths": 0,
                         "damage_dealt": 0, "damage_taken": 0, "heat_pts": 0.0}}
    gd["difficulty"].update(kw)
    return gd


# ── Scalar math ──

def test_scalar_starts_at_one():
    assert difficulty_scalar({}) == 1.0
    assert difficulty_scalar(_gd()) == 1.0


def test_scalar_weights_match_spec():
    assert RARITY_DIFF_WEIGHT["common"] == 0.25
    assert RARITY_DIFF_WEIGHT["uncommon"] == 0.5
    assert RARITY_DIFF_WEIGHT["rare"] == 1.0
    assert RARITY_DIFF_WEIGHT["legendary"] == 5.0


def test_scalar_hard_to_raise():
    # 20 common kills (5pts) + 20 days: 1 + 0.25 + 0.2 = 1.45. Still early game.
    gd = _gd(days=20, heat_pts=20 * 0.25)
    assert difficulty_scalar(gd) == 1.45


def test_scalar_caps_at_four():
    gd = _gd(days=365, heat_pts=1000.0)
    assert difficulty_scalar(gd) == SCALAR_MAX == 4.0


def test_scalar_grace_period():
    assert difficulty_scalar(_gd(days=10)) == 1.0  # first 10 days free
    assert difficulty_scalar(_gd(days=11)) == 1.02


def test_kill_heat_weighted_by_rarity():
    gd = _gd()
    add_kill_heat(gd, "common")
    assert gd["difficulty"]["heat_pts"] == 0.25
    add_kill_heat(gd, "legendary")
    assert gd["difficulty"]["heat_pts"] == 5.25  # one dragon = 21 commons
    add_kill_heat(gd, "fancy")
    assert gd["difficulty"]["heat_pts"] == 5.5  # unknown -> common weight


def test_legacy_saves_backfill_heat():
    gd = {"difficulty": {"turns": 50, "days": 5, "kills": 8}}  # no heat_pts key
    ensure_difficulty(gd)
    assert gd["difficulty"]["heat_pts"] == 2.0  # 8 kills as commons


# ── Clock ──

def test_node0_ages_world_every_turn():
    out = _run(node0_worldgen({"uuid": "d1", "prompt": "look", "game_data": {}}))
    assert out["game_data"]["difficulty"]["turns"] == 1
    assert out["game_data"]["difficulty"]["days"] == 0
    out2 = _run(node0_worldgen({"uuid": "d1", "prompt": "look", "game_data": out["game_data"]}))
    assert out2["game_data"]["difficulty"]["turns"] == 2


def test_ten_turns_make_a_day():
    gd = _gd(turns=19)
    advance_day_tracker(gd)
    assert gd["difficulty"]["turns"] == 20 and gd["difficulty"]["days"] == 2


# ── Spawn scaling (level AND stats) ──

def test_scalar_one_unchanged_baseline():
    m, _ = _ensure_target({}, "goblin", player_level=1)
    assert (m["level"], m["hp"], m["atk"]) == (1, 20, 5)


def test_scalar_scales_level_and_stats():
    # heat 40pts (160 commons) + day 60: 1 + 2.0 + 1.0 = 4.0 (capped).
    gd = _gd(turns=600, days=60, kills=160, heat_pts=40.0)
    assert difficulty_scalar(gd) == 4.0
    m, _ = _ensure_target(gd, "goblin", player_level=1)
    assert m["level"] == 4 and m["scalar"] == 4.0
    assert m["hp"] == 140  # (20 + 3*5) * 4
    assert m["atk"] == 24  # (5 + 1) * 4


def test_mid_scalar_partial_bump():
    gd = _gd(days=60, heat_pts=10.0)  # 1 + 0.5 + 1.0 = 2.5
    assert difficulty_scalar(gd) == 2.5
    m, _ = _ensure_target(gd, "goblin", player_level=2)
    assert m["level"] == 5  # round(2 * 2.5)
    assert m["hp"] == 100   # (20 + 4*5) * 2.5


def test_midfight_sheet_never_rescaled():
    gd = _gd(turns=999, days=99, kills=99, heat_pts=99.0)
    gd["monsters"] = [{"name": "goblin", "hp": 5, "max_hp": 20, "level": 1}]
    m, spawned = _ensure_target(gd, "goblin", player_level=1)
    assert spawned is False and m["level"] == 1 and m["hp"] == 5


# ── Density signal ──

def test_density_grows_with_scalar():
    base = [generate_cell("dense-seed", x, 0)["enemies"] for x in range(12)]
    same = [generate_cell("dense-seed", x, 0, scalar=1.0)["enemies"] for x in range(12)]
    assert same == base  # 1.0x adds nothing
    dense = [generate_cell("dense-seed", x, 0, scalar=4.0)["enemies"] for x in range(12)]
    assert [len(d) for d in dense] == [len(b) + 6 for b in base]  # +6 extra picks
    assert all(d[:len(b)] == b for d, b in zip(dense, base))  # base pack kept verbatim


def test_density_same_seed_same_pack():
    a = generate_cell("pack-seed", 7, -3, scalar=2.0)["enemies"]
    b = generate_cell("pack-seed", 7, -3, scalar=2.0)["enemies"]
    assert a == b


# ── Telemetry ──

def _snap(**kw):
    s = {
        "uuid": "u", "turn_id": "t1", "prompt": "attack!",
        "decision_report": {"intent": "attack", "target": "goblin", "monster_move": "attack"},
        "character_stats": {"level": 1, "health": 100, "max_health": 100,
                            "experience": 0, "experience_to_next": 100,
                            "strength": 10, "agility": 10, "dexterity": 10},
        "skills": [], "inventory": [], "relationships": [],
        "grid_data": {}, "game_data": _gd(),
    }
    s.update(kw)
    return s


def test_combat_tracks_damage_and_reports_scalar():
    out = _run(_damage_patch(_snap()))
    d = out["damage"]
    diff = out["game_data"]["difficulty"]
    assert diff["damage_dealt"] >= 0 and diff["damage_taken"] >= 0
    assert d["difficulty"]["scalar"] == 1.0


def test_kill_feeds_heat_and_counter():
    gd = _gd()
    gd["monsters"] = [{"name": "goblin", "hp": 1, "max_hp": 20, "ac": 5,
                       "agility": 3, "dexterity": 3, "atk": 1, "acc": 0,
                       "dmg_bonus": 0, "status": "hostile", "level": 1,
                       "rarity": "common", "tier": "normal", "xp_base": 10,
                       "loot": "", "type": "Humanoid"}]
    out = None
    for _ in range(20):
        out = _run(_damage_patch(_snap(game_data=gd)))
        if out["damage"]["killed"]:
            break
    assert out["damage"]["killed"] is True
    assert gd["difficulty"]["kills"] == 1
    assert gd["difficulty"]["heat_pts"] == 0.25
    assert gd["difficulty"]["damage_dealt"] > 0


def test_pipeline_tracks_days_and_reports_scalar(monkeypatch):
    from tests.test_new_player_scenarios import _Session
    s = _Session(monkeypatch, "heat-1")
    for i in range(6):
        s.act(f"attack the spider ({i})")
    out = s.act("attack the spider (final)")
    saved = s.saved()["game_data"]
    assert saved["difficulty"]["turns"] == 7
    assert saved["difficulty"]["damage_taken"] > 0  # retaliation telemetry lands
    # Week one barely moves the needle, even with a lucky early kill.
    assert difficulty_report(saved)["scalar"] < 1.1
    assert any("- difficulty: day" in t for t in out["tool_results"])
