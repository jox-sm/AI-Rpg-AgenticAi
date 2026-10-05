"""Run away: flee intent, pack engagement, stat/skill-driven escapes.

Deterministic core (dice decide, LLM only advises tricks). jev-model calls
are faked or forced into the offline fallback — no network in this file.
"""

import asyncio

import rpg_ai_server.agents.flee as flee_mod
from rpg_ai_server.agents.classifier import deterministic_pass
from rpg_ai_server.agents.flee import (
    adjudicate_trick,
    engage_pack,
    flee_chance,
    has_trick_item,
    live_hostiles,
    resolve_flee,
    skill_level,
)
from rpg_ai_server.agents.node4_parallel import _ensure_target, node4_parallel


def _run(coro):
    return asyncio.run(coro)


def _stats(**kw):
    s = {"level": 1, "health": 100, "max_health": 100, "experience": 0,
         "experience_to_next": 100, "strength": 10, "agility": 10, "dexterity": 10}
    s.update(kw)
    return s


def _snap(**kw):
    s = {
        "uuid": "u", "turn_id": "t1", "prompt": "run away!",
        "decision_report": {"intent": "flee", "flee_method": "run", "skill_hint": "",
                            "target": "", "monster_move": "attack"},
        "character_stats": _stats(), "skills": [], "inventory": [],
        "relationships": [], "grid_data": {}, "game_data": {},
    }
    s.update(kw)
    return s


def _goblin(hp=20, **kw):
    m = {"name": "goblin", "hp": hp, "max_hp": 20, "ac": 12, "agility": 14,
         "dexterity": 12, "atk": 5, "acc": 3, "dmg_bonus": 1, "status": "hostile",
         "level": 1, "rarity": "common", "tier": "normal", "xp_base": 10,
         "loot": "", "type": "Humanoid"}
    m.update(kw)
    return m


# ── Intent ──

def test_flee_verbs_detected():
    for p in ("run away!", "flee!", "escape!", "retreat!", "I run", "bolt!", "fall back"):
        out = deterministic_pass(p, False)
        assert out is not None and out["intent"] == "flee", p
        assert out["monster_move"] == "attack"


def test_trick_method_detected():
    out = deterministic_pass("throw sand and run!", False)
    assert out["intent"] == "flee" and out["flee_method"] == "trick"
    out = deterministic_pass("detonate explosives to escape", False)
    assert out["flee_method"] == "trick"
    out = deterministic_pass("just run!", False)
    assert out["flee_method"] == "run"


def test_attack_still_wins_and_explore_untouched():
    assert deterministic_pass("attack the goblin", False)["intent"] == "attack"
    assert deterministic_pass("go north", False) is None


def test_classifier_llm_path_carries_flee_fields(monkeypatch):
    from rpg_ai_server.agents import classifier as clf

    async def fake_chat_json(**kw):
        return {"intent": "flee", "flee_method": "trick", "skill_hint": "acrobatics",
                "confidence": 0.9, "reason": "t"}

    monkeypatch.setattr("rpg_ai_server.agents.classifier.chat_json", fake_chat_json)
    out = _run(clf.classifier_node({"uuid": "u", "prompt": "I backflip away quizzically", "images": {}}))
    assert out["decision_report"]["intent"] == "flee"
    assert out["decision_report"]["flee_method"] == "trick"
    assert out["decision_report"]["skill_hint"] == "acrobatics"


# ── Engagement ──

def test_engage_pack_caps_and_flags():
    gd = {"monsters": [_goblin(), _goblin(), _goblin(), _goblin(), _goblin(),
                       {"name": "ghost", "hp": 10, "status": "neutral"},
                       {"name": "corpse", "hp": 0, "status": "hostile"}]}
    pack = engage_pack(gd)
    assert len(pack) == 4
    assert all(m["engaged"] for m in pack)
    assert gd["monsters"][4]["engaged"] is False  # 5th waits out
    assert [m["name"] for m in live_hostiles(gd)].count("goblin") == 5


def test_currently_engaged_empty_without_fight():
    assert engage_pack({"monsters": []}) == []


# ── Chance math ──

def test_flee_chance_agility_rules():
    import pytest
    solo = []
    assert flee_chance(10, 10, solo) == pytest.approx(0.55)
    assert flee_chance(20, 10, solo) == pytest.approx(0.95)  # capped
    assert flee_chance(1, 1, solo) == pytest.approx(0.10)  # 0.55-0.36-0.09, above floor
    assert flee_chance(10, 10, [_goblin()]) == pytest.approx(0.34)  # -0.15, -0.06 gap
    assert flee_chance(10, 10, [_goblin(), _goblin(), _goblin()]) == pytest.approx(0.05)  # mobbed


def test_blinded_pursuer_no_penalty():
    import pytest
    blind = _goblin(blinded=2)
    assert flee_chance(10, 10, [blind]) == pytest.approx(0.49)  # only the speed gap bites


def test_skill_and_item_helpers():
    skills = [{"name": "Acrobatics", "skill_type": "dexterity", "level": 3, "cooldown": 0,
               "max_cooldown": 1, "description": ""}]
    assert skill_level(skills, "acrobatics") == 3
    assert skill_level(skills, "spear") == 0
    inv = [{"item_id": "x", "name": "Smoke Bomb"}]
    assert has_trick_item(inv) == "Smoke Bomb"
    assert has_trick_item([{"item_id": "y", "name": "Stick"}]) is None


# ── jev adjudication ──

def test_adjudication_falls_back_offline(monkeypatch):
    from rpg_ai_server.config.settings import settings
    monkeypatch.setattr(settings.models, "jev_model", "")
    out = _run(adjudicate_trick("throw sand and run", _stats(), [], [], [_goblin()], "desert"))
    assert out["blind"] is True and out["bonus"] > 0
    assert out["damage"] == "0"


def test_adjudication_fallback_explosives(monkeypatch):
    from rpg_ai_server.config.settings import settings
    monkeypatch.setattr(settings.models, "jev_model", "")
    inv = [{"item_id": "dyn", "name": "Dynamite"}]
    out = _run(adjudicate_trick("blow them up and run", _stats(), [], inv, [_goblin()], ""))
    assert out["damage"] == "1d6" and out["skill"] == "explosives" and out["bonus"] >= 0.2


def test_adjudication_parses_jev_json(monkeypatch):
    async def fake_chat_json(**kw):
        return {"skill": "acrobatics", "stat": "charisma", "bonus": 0.9,
                "blind": True, "damage": "0", "reason": "sand"}

    monkeypatch.setattr("rpg_ai_server.utils.openrouter_client.chat_json", fake_chat_json)
    out = _run(adjudicate_trick("sand run", _stats(), [], [], [_goblin()], "desert"))
    assert out["skill"] == "acrobatics"
    assert out["stat"] == "agility"  # charisma rejected
    assert out["bonus"] == 0.4       # clamped
    assert out["blind"] is True


# ── Resolution ──

def test_flee_success_disengages(monkeypatch):
    monkeypatch.setattr(flee_mod, "_roll_d100", lambda: 1)  # rolled 1: always out
    gd = {"monsters": [_goblin(), _goblin()]}
    out = _run(resolve_flee(_snap(game_data=gd)))
    f = out["flee"]
    assert f["success"] is True and f["xp_award"] == 0
    assert all(m["engaged"] is False for m in gd["monsters"])
    assert out["character_stats"]["health"] == 100
    assert f["player_hp_after"] == 100


def test_flee_fail_opportunity_strikes_entire_pack(monkeypatch):
    monkeypatch.setattr(flee_mod, "_roll_d100", lambda: 100)  # always caught
    gd = {"monsters": [_goblin(), _goblin()]}
    out = _run(resolve_flee(_snap(game_data=gd)))
    f = out["flee"]
    assert f["success"] is False
    assert len(f["rounds"]) == 2  # one opportunity strike per pursuer
    assert all(r.get("opportunity") for r in f["rounds"])
    assert all(m["engaged"] for m in gd["monsters"])  # still on you


def test_flee_nothing_there_trivial():
    out = _run(resolve_flee(_snap(game_data={"monsters": []})))
    assert out["flee"]["success"] is True
    assert out["flee"]["escaped"] == []


def test_flee_trick_blinds_pack(monkeypatch):
    from rpg_ai_server.config.settings import settings
    monkeypatch.setattr(settings.models, "jev_model", "")  # force fallback
    monkeypatch.setattr(flee_mod.random, "randint", lambda a, b: 1)
    gd = {"monsters": [_goblin(), _goblin()]}
    snap = _snap(game_data=gd, prompt="throw sand in their eyes and run!",
                 decision_report={"intent": "flee", "flee_method": "trick",
                                  "skill_hint": "", "target": "", "monster_move": "attack"})
    out = _run(resolve_flee(snap))
    f = out["flee"]
    assert f["method"] == "trick" and f["blind_applied"] is True
    assert all(m.get("blinded") == 2 for m in gd["monsters"])
    assert f["success"] is True


def test_blind_weakens_retaliation():
    m = _goblin(blinded=2, acc=10)
    from rpg_ai_server.agents.flee import monster_strike
    _, acc = monster_strike(m, 10)
    assert acc == 6 and m["blinded"] == 1  # -4 wild swing, ticks down


def test_corpse_cannot_flee():
    stats = _stats(health=0, is_dead=True)
    out = _run(resolve_flee(_snap(character_stats=stats, game_data={"player_dead": True})))
    assert out["flee"]["rounds"] == [] and out["flee"]["success"] is False
    assert out["character_stats"]["is_dead"] is True


# ── Pack combat ──

def test_pack_retaliation_hits_from_everyone():
    from rpg_ai_server.agents.node4_parallel import node4_parallel as n4
    gd: dict = {}
    _ensure_target(gd, "goblin", player_level=1)
    _ensure_target(gd, "wolf", player_level=1)
    snap = {"uuid": "u", "turn_id": "t", "prompt": "attack!",
            "decision_report": {"intent": "attack", "target": "goblin", "monster_move": "attack"},
            "character_stats": dict(_stats()), "skills": [], "inventory": [],
            "relationships": [], "grid_data": {}, "game_data": gd}
    out = _run(n4(snap))
    d = out["mechanics_patches"]["damage"]["damage"]
    assert d["pack"] and len(d["pack"]) == 2
    by = {r.get("by") for r in d["rounds"] if r.get("side") == "monster"}
    assert by == {"goblin", "wolf"}


def test_double_kill_sums_xp_and_loot():
    gd = {"monsters": [_goblin(hp=1, name="goblin"), _goblin(hp=1, name="rat",
                                                             agility=3, dexterity=3)]}
    snap = {"uuid": "u", "turn_id": "t", "prompt": "spin attack!",
            "decision_report": {"intent": "attack", "target": "goblin", "monster_move": "attack"},
            "character_stats": dict(_stats(agility=30, dexterity=30)),  # 3 strikes, player first
            "skills": [], "inventory": [], "relationships": [],
            "grid_data": {}, "game_data": gd}
    from rpg_ai_server.agents.node4_parallel import node4_parallel as n4
    got = None
    for _ in range(10):
        out = _run(n4(dict(snap, game_data={"monsters": [dict(m) for m in gd["monsters"]]})))
        d = out["mechanics_patches"]["damage"]["damage"]
        if len(d.get("slain", [])) == 2:
            got = d
            break
    assert got is not None and got["xp_award"] > 3  # two kills pay more than one


# ── Pipeline ──

def _flee_aware_session(monkeypatch, sid):
    import tests.test_new_player_scenarios as sc

    orig_fake = sc._fake_classifier

    async def flee_fake(state):
        low = str(state.get("prompt", "")).lower()
        if any(w in low for w in ("run away", "flee", "escape", "retreat", "run", "bolt")):
            method = "trick" if any(k in low for k in ("sand", "bomb", "smoke", "throw")) else "run"
            return {"decision_report": {"intent": "flee", "target": "", "flee_method": method,
                                        "skill_hint": "", "monster_move": "attack", "buffs": [],
                                        "debuffs": [], "damage_hint": "", "needs_search": False,
                                        "needs_image": False, "needs_redescribe": False,
                                        "search_query": "", "confidence": 0.95, "reason": "t"},
                    "needs_search": False, "needs_image_processing": False,
                    "needs_re_description": False}
        return await orig_fake(state)

    monkeypatch.setattr(sc, "_fake_classifier", flee_fake)
    return sc._Session(monkeypatch, sid)


def test_pipeline_run_away_disengages(monkeypatch):
    s = _flee_aware_session(monkeypatch, "flee-1")
    s.act("attack the goblin")
    assert any(m.get("engaged") for m in s.saved()["game_data"]["monsters"])
    monkeypatch.setattr(flee_mod, "_roll_d100", lambda: 1)  # clean getaway
    out = s.act("run away!")
    assert out["story"]
    assert not any(m.get("engaged") for m in s.saved()["game_data"]["monsters"])
    assert any("- flee:" in t for t in out["tool_results"])


def test_pipeline_pack_fight_retaliates_twice(monkeypatch):
    s = _flee_aware_session(monkeypatch, "flee-2")
    s.act("attack the goblin")
    out = s.act("attack the wolf")
    names = [m["name"] for m in out["game_data"]["monsters"]]
    assert "goblin" in names and "wolf" in names
    assert any("strikes you" in t for t in out["tool_results"])


def test_pipeline_trick_uses_mocked_jev_skill(monkeypatch):
    async def fake_jev(*a, **kw):
        return {"skill": "acrobatics", "stat": "agility", "bonus": 0.3,
                "blind": True, "damage": "0", "reason": "sand wave"}

    s = _flee_aware_session(monkeypatch, "flee-3")
    s.act("attack the goblin")
    monkeypatch.setattr("rpg_ai_server.agents.flee.adjudicate_trick", fake_jev)
    monkeypatch.setattr(flee_mod.random, "randint", lambda a, b: 1)  # the trick works
    out = s.act("kick sand in their eyes and run!")
    assert any("acrobatics" in t for t in out["tool_results"])
    saved = s.saved()["game_data"]["monsters"]
    assert not any(m.get("engaged") for m in saved if int(m.get("hp", 0) or 0) > 0)
    assert any(int(m.get("blinded", 0) or 0) > 0 for m in saved)
