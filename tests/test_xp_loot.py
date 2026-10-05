"""XP formula, probability loot, death contract, stat normalization.

Formula: kill_xp = round_half_up(xp_base * level * rarity_mult * tier_mult * type_mult).
Loot: item-db enemy rows, rolled with rarity luck. Death: is_dead persists and
the output carries game_over for the frontend to close the game.
"""

import asyncio
import random

from rpg_ai_server.agents.node4_parallel import _damage_patch, _ensure_target, node4_parallel
from rpg_ai_server.schemas.types import GameOutput
from rpg_ai_server.scripts.xp_loot import (
    STAT_MAX,
    STAT_MIN,
    apply_level_ups,
    clamp_stat,
    enemy_db_row,
    kill_xp,
    merge_loot,
    normalize_rarity,
    normalize_tier,
    parse_level_range,
    parse_loot_string,
    participation_tick,
    roll_loot,
    round_half_up,
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
                            "experience": 0, "experience_to_next": 100,
                            "strength": 10, "agility": 10, "dexterity": 10},
        "skills": [], "inventory": [], "relationships": [],
        "grid_data": {}, "game_data": {},
    }
    s.update(kw)
    return s


# ── Formula ──

def test_common_goblin_xp_formula():
    # 10 * 1 * 0.25 = 2.5 -> 3
    assert kill_xp(10, 1, "common") == 3


def test_rarity_ladder():
    assert kill_xp(10, 1, "uncommon") == 5    # 10 * 1 * 0.5
    assert kill_xp(10, 1, "rare") == 10
    assert kill_xp(10, 1, "epic") == 20
    assert kill_xp(10, 1, "legendary") == 40
    assert kill_xp(10, 1, "mythic") == 80


def test_level_and_tier_and_type_scale():
    assert kill_xp(10, 3, "common") == 8              # 10 * 3 * 0.25 = 7.5 -> 8
    assert kill_xp(10, 1, "common", tier="elite") == 4   # 2.5 * 1.5 = 3.75 -> 4
    assert kill_xp(10, 1, "common", tier="boss") == 8    # 2.5 * 3 = 7.5 -> 8
    assert kill_xp(10, 1, "common", mtype="dragon") == 5  # 2.5 * 2.0
    assert kill_xp(10, 1, "common", mtype="whatever") == 3


def test_unknown_rarity_tier_fall_back():
    assert normalize_rarity("fancy") == "common"
    assert normalize_tier("miniboss") == "normal"
    assert kill_xp("junk", "junk", "junk") >= 1
    assert round_half_up(2.5) == 3


def test_participation_tick_is_fraction():
    assert participation_tick(3) == 1
    assert participation_tick(100) == 25
    assert participation_tick(0) == 1


# ── DB grounding ──

def test_goblin_row_grounds_sheet():
    row = enemy_db_row("Goblin")
    assert row is not None and int(row["XP"]) == 10
    lo, hi = parse_level_range(row["Level Range"])
    assert (lo, hi) == (1, 3)
    assert ("item", "Rusty Dagger") in parse_loot_string(row["Loot"])
    assert ("gold", "5") in parse_loot_string(row["Loot"])


def test_spawn_uses_db_level_cap_and_loot():
    gd: dict = {}
    m, _ = _ensure_target(gd, "goblin", player_level=1)
    assert m["level"] == 1 and m["hp"] == 20
    assert m["rarity"] == "common" and m["xp_base"] == 10
    assert "Goblin Ear" in m["loot"]
    gd2: dict = {}
    m2, _ = _ensure_target(gd2, "goblin", player_level=99)
    assert m2["level"] == 3 and m2["hp"] == 30  # capped by row max, +5/level


def test_parse_level_range_defaults():
    assert parse_level_range("4-6") == (4, 6)
    assert parse_level_range("7") == (7, 7)
    assert parse_level_range(None) == (1, 1)


# ── Loot rolls ──

def test_kill_grants_loot_from_db_probabilities():
    random.seed(7)
    sheet = {"name": "Goblin", "rarity": "common", "tier": "normal",
             "loot": "Rusty Dagger, Goblin Ear, 5 Gold"}
    seen_names: set = set()
    for _ in range(30):
        for drop in roll_loot(sheet):
            seen_names.add(drop["name"])
            assert drop["quantity"] >= 1 and drop["item_id"]
    assert seen_names  # 30 common rolls land something
    assert "Gold" in seen_names  # 1/3 of candidates, 50% odds -> certain over 30 rolls


def test_legendary_luck_beats_common():
    sheet_c = {"name": "X", "rarity": "common", "tier": "normal", "loot": "A, B, C, D"}
    sheet_l = {"name": "X", "rarity": "legendary", "tier": "normal", "loot": "A, B, C, D"}
    random.seed(11)
    n_c = sum(len(roll_loot(sheet_c)) for _ in range(40))
    random.seed(11)
    n_l = sum(len(roll_loot(sheet_l)) for _ in range(40))
    assert n_l > n_c


def test_no_loot_without_kill():
    out = _run(_damage_patch(_snap()))  # goblin survives a single fresh swing often enough...
    d = out["damage"]
    if not d["killed"]:
        assert d["loot"] == []
        assert d["xp_award"] == participation_tick(kill_xp(10, 1, "common"))


def test_merge_loot_stacks_gold():
    inv = [{"item_id": "gold", "name": "Gold", "quantity": 5}]
    merged = merge_loot(inv, [{"item_id": "gold", "name": "Gold", "quantity": 7},
                              {"item_id": "goblin-ear", "name": "Goblin Ear", "quantity": 1}])
    gold = next(i for i in merged if i["item_id"] == "gold")
    assert gold["quantity"] == 12 and len(merged) == 2


# ── XP application + levels ──

def test_xp_applies_and_levels_up():
    stats = {"level": 1, "experience": 99, "experience_to_next": 100,
             "health": 40, "max_health": 100}
    events = apply_level_ups(stats, 3)
    assert stats["level"] == 2 and stats["experience"] == 2
    assert stats["experience_to_next"] == 200
    assert stats["health"] == 110 and stats["max_health"] == 110
    assert any("LEVEL UP" in e for e in events)


def test_pipeline_kill_pays_formula_xp_and_loot_lines(monkeypatch):
    from tests.test_new_player_scenarios import _Session
    s = _Session(monkeypatch, "xp-1")
    last = None
    for i in range(40):
        last = s.act(f"slay the goblin ({i})")
        if last["game_data"]["monsters"][0].get("status") == "dead":
            break
    assert last["game_data"]["monsters"][0].get("status") == "dead"
    assert any("loot:" in t for t in last["tool_results"])
    assert any("+3xp" in t for t in last["tool_results"])  # 10 * 1 * 0.25 -> 3
    cs = last["game_data"]["character_stats"]
    assert (cs["experience"] if isinstance(cs, dict) else cs.experience) >= 3


# ── Death contract ──

def test_dead_flag_persists_and_game_over_set():
    sheet = {"name": "ogre", "hp": 500, "max_hp": 500, "ac": 5, "agility": 3, "dexterity": 3,
             "atk": 120, "acc": 20, "dmg_bonus": 20, "status": "hostile",
             "level": 1, "rarity": "rare", "tier": "normal", "xp_base": 40,
             "loot": "", "type": "Humanoid"}
    snap = _snap(game_data={"monsters": [sheet]},
                 decision_report={"intent": "attack", "target": "ogre", "monster_move": "attack"})
    out = _run(node4_parallel(snap))
    assert out["character_stats"]["is_dead"] is True
    assert out["character_stats"]["health"] == 0
    assert out["game_data"]["player_dead"] is True
    assert any("YOU ARE DOWN" in t for t in out["tool_results"][0].splitlines())

    from rpg_ai_server.agents.node7_output_pusher import node7_output_pusher
    from rpg_ai_server.redis.output_cache import OutputCache
    from tests.fakes import FakeOutputClient
    fake = FakeOutputClient()
    state = dict(snap)
    state.update(out)
    state["uuid"] = "dead-1"
    state["story_output"] = "You fall."
    pushed = _run(node7_output_pusher(state, OutputCache(fake)))
    assert pushed["processed"] is True
    cached = fake.data["dead-1"]
    assert cached["game_over"] is True
    assert cached["game_data"]["character_stats"]["is_dead"] is True
    assert GameOutput(**cached).game_over is True


def test_corpse_turn_is_quiet():
    stats = {"level": 1, "health": 0, "max_health": 100, "experience": 0,
             "experience_to_next": 100, "strength": 10, "agility": 10,
             "dexterity": 10, "is_dead": True}
    out = _run(_damage_patch(_snap(character_stats=stats, game_data={"player_dead": True})))
    d = out["damage"]
    assert d["rounds"] == [] and d["xp_award"] == 0 and d["loot"] == []
    assert out["character_stats"]["is_dead"] is True
    assert out["game_data"]["player_dead"] is True


# ── Stat normalization ──

def test_baby_stats_clamped_up():
    assert clamp_stat(1) == STAT_MIN == 3
    assert clamp_stat(2) == 3
    assert clamp_stat(10) == 10
    assert clamp_stat(999) == STAT_MAX == 30
    assert clamp_stat("junk") == 10


def test_spawn_table_within_mortal_scale():
    from rpg_ai_server.agents.node4_parallel import _SPAWN_TABLE
    for key, s in _SPAWN_TABLE.items():
        assert STAT_MIN <= s["agility"] <= STAT_MAX, key
        assert STAT_MIN <= s["dexterity"] <= STAT_MAX, key
        assert s["rarity"] in ("common", "uncommon", "rare", "epic", "legendary", "mythic"), key
