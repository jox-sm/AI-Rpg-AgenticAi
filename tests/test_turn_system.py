"""Speed-based turn system: order + multi-attacks + monster retaliation.

speed = agility + dexterity. Faster side strikes first; +1 strike per 50%
speed edge (cap 4/side). Pure logic except the two marked pipeline tests,
which reuse the offline playthrough harness (no network).
"""

import asyncio

from rpg_ai_server.agents.node4_parallel import (
    _damage_patch,
    _ensure_target,
    _speed_of_agidex,
    _strikes_for,
    node4_parallel,
)


def _run(coro):
    return asyncio.run(coro)


def _snap(**kw):
    s = {
        "uuid": "u",
        "turn_id": "t1",
        "prompt": "attack!",
        "decision_report": {"intent": "attack", "target": "goblin", "monster_move": "attack"},
        "character_stats": {"level": 1, "health": 100, "max_health": 100,
                            "strength": 10, "agility": 10, "dexterity": 10},
        "skills": [], "inventory": [], "relationships": [],
        "grid_data": {}, "game_data": {},
    }
    s.update(kw)
    return s


# ── Strike table ──

def test_strikes_equal_speed_single():
    assert _strikes_for(20, 20) == 1


def test_strikes_double_speed_triple():
    assert _strikes_for(40, 20) == 3  # the "twice as fast" case


def test_strikes_half_edge_bonus():
    assert _strikes_for(30, 20) == 2
    assert _strikes_for(28, 20) == 1  # 40% edge is not enough


def test_strikes_capped():
    assert _strikes_for(60, 20) == 4
    assert _strikes_for(1000, 20) == 4


def test_speed_defaults():
    assert _speed_of_agidex(10, 10) == 20
    assert _speed_of_agidex(None, None) == 20


# ── Sheets ──

def test_spawn_sheet_has_speed_stats():
    gd: dict = {}
    m, spawned = _ensure_target(gd, "spider")
    assert spawned is True
    assert (m["agility"], m["dexterity"]) == (20, 20)
    assert m["atk"] > 0 and m["ac"] >= 10


def test_legacy_sheet_migrated():
    gd = {"monsters": [{"name": "goblin", "hp": 20}]}
    m, spawned = _ensure_target(gd, "goblin")
    assert spawned is False
    assert m["agility"] == 14 and m["dexterity"] == 12
    assert m["max_hp"] == 20 and m["status"] == "hostile"


# ── Turn resolution ──

def test_slow_monster_player_first_single_strikes():
    out = _run(_damage_patch(_snap()))
    d = out["damage"]
    assert d["order"] == ["player", "pack"] or d["order"] == ["pack", "player"]
    # goblin speed 26 vs player 20: goblin first, but only 1 strike each
    assert d["order"] == ["pack", "player"]
    assert d["player_strikes"] == 1 and d["monster_strikes"] == 1
    assert out["character_stats"]["health"] <= 100


def test_double_speed_monster_strikes_thrice_first():
    snap = _snap(decision_report={"intent": "attack", "target": "spider", "monster_move": "attack"})
    outs = [_run(_damage_patch(dict(snap, game_data={}))) for _ in range(20)]
    assert all(o["damage"]["order"] == ["pack", "player"] for o in outs)
    assert all(o["damage"]["monster_strikes"] == 3 for o in outs)
    assert all(o["damage"]["player_strikes"] == 1 for o in outs)
    assert any(o["damage"]["player_hp_after"] < 100 for o in outs)  # retaliation lands


def test_fast_player_strikes_thrice():
    stats = {"level": 5, "health": 100, "max_health": 100,
             "strength": 10, "agility": 30, "dexterity": 30}  # speed 60 vs goblin 26
    out = _run(_damage_patch(_snap(character_stats=stats)))
    d = out["damage"]
    assert d["order"] == ["player", "pack"]
    assert d["player_strikes"] == 3 and d["monster_strikes"] == 1


def _fresh_weak_goblin():
    return {"monsters": [{"name": "goblin", "hp": 1, "max_hp": 20, "ac": 12,
                          "agility": 1, "dexterity": 1, "atk": 1, "acc": 0,
                          "dmg_bonus": 0, "status": "hostile"}]}


def test_kill_before_retaliation_no_player_damage():
    # atk 1 + d6 vs AC 10 can never deal damage, so the player is safe;
    # loop until the 55%-chance player swing connects.
    killing = None
    for _ in range(20):
        out = _run(_damage_patch(_snap(game_data=_fresh_weak_goblin())))
        if out["damage"]["killed"]:
            killing = out["damage"]
            break
    assert killing is not None
    assert killing["player_hp_after"] == 100
    assert not [r for r in killing["rounds"] if r["side"] == "monster"]


def test_player_down_stops_and_no_xp():
    # atk 120 one-shots through any roll: 120 + (d6+20) - 10 > 100 always.
    gd = {"monsters": [{"name": "ogre", "hp": 500, "max_hp": 500, "ac": 5,
                        "agility": 1, "dexterity": 1, "atk": 120, "acc": 20,
                        "dmg_bonus": 20, "status": "hostile"}]}
    snap = _snap(game_data=gd, decision_report={"intent": "attack", "target": "ogre",
                                                              "monster_move": "attack"})
    out = _run(_damage_patch(snap))
    d = out["damage"]
    assert d["player_down"] is True
    assert d["player_hp_after"] == 0
    assert d["xp_award"] == 0
    assert out["character_stats"]["health"] == 0
    # downed mid-turn: no further strikes after the dropping blow
    assert d["rounds"][-1]["side"] == "monster"


def test_node4_merge_carries_health_and_round_lines():
    state = _snap(decision_report={"intent": "attack", "target": "spider", "monster_move": "attack"})
    out = _run(node4_parallel(state))
    assert out["character_stats"]["health"] <= 100
    text = out["tool_results"][0]
    assert "spd 20 vs 40" in text
    assert text.count("strikes you") == 3
    assert "- damage: attack spider" in text


def test_non_attack_skips_turn():
    out = _run(_damage_patch(_snap(decision_report={"intent": "explore"})))
    assert out["damage"] == {"skipped": True}
    assert "character_stats" not in out and "game_data" not in out


# ── Full pipeline ──

def test_pipeline_spider_triple_strike_and_bleed(monkeypatch):
    from tests.test_new_player_scenarios import _Session
    s = _Session(monkeypatch, "fast-1")
    hurt = False
    for i in range(6):
        out = s.act(f"attack the spider ({i})")
        cs = out["game_data"]["character_stats"]
        hp = cs["health"] if isinstance(cs, dict) else cs.health
        if hp < 100:
            hurt = True
            break
    assert hurt
    assert out["tool_results"] and "strikes you" in out["tool_results"][-1]


def test_pipeline_goblin_retaliates_over_time(monkeypatch):
    from tests.test_new_player_scenarios import _Session
    s = _Session(monkeypatch, "fast-2")
    hps = []
    for i in range(10):
        out = s.act(f"slay the goblin ({i})")
        cs = out["game_data"]["character_stats"]
        hps.append(cs["health"] if isinstance(cs, dict) else cs.health)
        if out["game_data"]["monsters"][0].get("status") == "dead":
            break
    assert hps[-1] <= hps[0]
    assert any("strikes you" in t for t in out["tool_results"])
