"""Brand-new-player playthroughs: full pipeline, zero network.

Real orchestrator + real compiled graph v2 + real worldgen + real mechanics.
Only the LLM/network nodes (classifier/search/image/redescribe/summarizer/story)
are deterministic offline fakes. No OpenRouter, no httpx, no Upstash.
"""

import asyncio
import copy

import rpg_ai_server.engine.graph_v2 as gv2
from rpg_ai_server.engine.orchestrator import GameOrchestrator
from rpg_ai_server.redis.game_state import GameStateManager
from rpg_ai_server.redis.output_cache import OutputCache
from rpg_ai_server.schemas.types import ContextSummary, GameRequest
from rpg_ai_server.scripts.world_generator import generate_cell, get_world_cell
from tests.fakes import FakeGamesClient, FakeOutputClient

_MONSTERS = ("goblin", "dragon", "wolf", "skeleton", "orc", "spider", "troll", "ogre", "rat", "bandit", "giant")


def _run(coro):
    return asyncio.run(coro)


# ── Offline fakes (deterministic, no network) ──

async def _fake_classifier(state):
    low = str(state.get("prompt", "")).lower()
    intent, target = "explore", ""
    for name in _MONSTERS:
        if name in low:
            target = name
            break
    if any(w in low for w in ("slay", "attack", "kill", "hit", "strike", "smite", "fight", "shoot", "stab", "smash")):
        intent = "attack"
        target = target or "foe"
    needs_search = ("lore" in low and ("about" in low or "tell" in low)) or "what is a" in low
    return {
        "decision_report": {
            "intent": intent, "target": target, "monster_move": "attack",
            "buffs": [], "debuffs": [], "damage_hint": "",
            "needs_search": needs_search, "needs_image": False, "needs_redescribe": False,
            "search_query": target or "dragon", "confidence": 0.95, "reason": "offline-fake",
        },
        "needs_search": needs_search,
        "needs_image_processing": False,
        "needs_re_description": False,
    }


async def _fake_search(state):
    rep = state.get("decision_report") or {}
    q = rep.get("search_query", "lore") if isinstance(rep, dict) else "lore"
    return {"search_results": f"Lore about {q}: ancient tale from the offline archive. " * 4,
            "needs_search": False}


async def _fake_image(state):
    return {"needs_image_processing": False}


async def _fake_redescribe(state):
    return {"needs_re_description": False}


async def _fake_summarizer(state):
    gd = state.get("game_data") or {}
    pos = gd.get("player_pos") or {}
    cell = get_world_cell(gd, pos.get("x", 0), pos.get("y", 0))
    biome = cell.get("biome", "Unknown") if isinstance(cell, dict) else "Unknown"
    tools = state.get("tool_results") or []
    return {"context_summary": ContextSummary(
        current_location=f"({pos.get('x')},{pos.get('y')}) {biome}",
        recent_events=[str(t)[:200] for t in tools[-3:]],
        narrative_context=f"Standing at ({pos.get('x')},{pos.get('y')}) in {biome}.",
    )}


async def _fake_story(state):
    gd = state.get("game_data") or {}
    pos = gd.get("player_pos") or {}
    cell = get_world_cell(gd, pos.get("x", 0), pos.get("y", 0))
    biome = cell.get("biome", "Unknown") if isinstance(cell, dict) else "Unknown"
    tools = state.get("tool_results") or []
    tail = str(tools[-1])[:220] if tools else "nothing happens"
    return {"story_output": (
        f"You {state.get('prompt', 'look around')} at ({pos.get('x')},{pos.get('y')}) — {biome}. {tail}"
    )}


def _patch_offline(monkeypatch):
    monkeypatch.setattr(gv2, "classifier_node", _fake_classifier)
    monkeypatch.setattr(gv2, "node1_web_search", _fake_search)
    monkeypatch.setattr(gv2, "node2_image_processor", _fake_image)
    monkeypatch.setattr(gv2, "node3_redescriptor", _fake_redescribe)
    monkeypatch.setattr(gv2, "node5_context_injector", _fake_summarizer)
    monkeypatch.setattr(gv2, "node6_story_generator", _fake_story)


class _Session:
    """One player's full stack: orchestrator + compiled graph + fake backends."""

    def __init__(self, monkeypatch, sid):
        _patch_offline(monkeypatch)
        self.sid = sid
        self.games = FakeGamesClient()
        self.out_client = FakeOutputClient()
        cache = OutputCache(self.out_client)
        self.gsm = GameStateManager(self.games, memory=None)
        self.orch = GameOrchestrator(cache, self.gsm, worker_id=f"w-{sid}")
        self.orch.compiled_graph = gv2.build_game_graph_v2(cache).compile()

    def act(self, prompt):
        out = _run(self.orch.process_request(GameRequest(uuid=self.sid, prompt=prompt)))
        assert out is not None and "error" not in out, f"turn failed: {out}"
        return out

    def saved(self):
        return _run(self.gsm.load_state(self.sid))

    def pos(self):
        return self.saved()["game_data"]["player_pos"]

    def grid(self):
        return self.saved()["game_data"]["grid"]


# ── Day-one combat ──

def test_slay_goblin_first_turn(monkeypatch):
    s = _Session(monkeypatch, "newbie-1")
    out = s.act("slay a goblin with a sword")
    assert "goblin" in out["story"].lower()
    assert any("damage: attack" in line and "goblin" in line.lower() for line in out["tool_results"])
    monsters = out["game_data"].get("monsters", [])
    assert len(monsters) == 1 and monsters[0]["hp"] <= 20
    assert s.pos() == {"x": 3, "y": 3, "depth": 0}  # combat does not move you


def test_attack_twice_hp_drops_or_dies(monkeypatch):
    s = _Session(monkeypatch, "newbie-2")
    first = s.act("attack the goblin")
    second = s.act("attack the goblin again")
    m1 = first["game_data"]["monsters"][0]["hp"]
    m2 = second["game_data"]["monsters"][0]["hp"]
    assert m2 <= m1  # second swing never heals
    assert second["game_data"]["monsters"][0]["name"].lower() == "goblin"


def test_goblin_eventually_dies(monkeypatch):
    # No round cap (dice are unseeded) — but the loop ends on EITHER death.
    # A dead player ends the fight just as finally as a dead goblin; without
    # the player check this loops forever on runs where the goblin wins.
    s = _Session(monkeypatch, "newbie-3")
    swings = 0
    while True:
        swings += 1
        last = s.act(f"hit the goblin ({swings})")
        goblin = last["game_data"]["monsters"][0]
        you_hp = (last["game_data"].get("character_stats", {}) or {}).get("health", 1)
        if goblin.get("status") == "dead" or you_hp <= 0:
            break
        # Failsafe against a genuinely stuck fight (not luck).
        assert swings < 1000, "1000 swings with no resolution — combat is stuck"
    assert goblin.get("status") == "dead", \
        f"you died on swing {swings} with goblin at {goblin.get('hp')}hp — balance issue?"
    assert you_hp > 0


def test_dragon_fight_spawns_dragon_sheet(monkeypatch):
    s = _Session(monkeypatch, "newbie-4")
    out = s.act("I shoot my bow at the dragon!")
    names = [m["name"].lower() for m in out["game_data"]["monsters"]]
    assert "dragon" in names
    assert out["game_data"]["monsters"][0]["hp"] <= 150


def test_dice_rolls_every_turn(monkeypatch):
    s = _Session(monkeypatch, "newbie-5")
    out = s.act("hello?")
    assert any("dice: roll=" in line for line in out["tool_results"])


# ── "Where am I?" / "take me somewhere" ──

def test_where_am_i_reports_biome_and_coords(monkeypatch):
    s = _Session(monkeypatch, "lost-1")
    out = s.act("where am I?")
    cell = get_world_cell(out["game_data"], 3, 3)
    assert cell["biome"] in out["story"]
    assert "(3,3)" in out["story"]
    assert s.pos() == {"x": 3, "y": 3, "depth": 0}  # asking does not teleport


def test_wishful_travel_does_not_teleport(monkeypatch):
    s = _Session(monkeypatch, "lost-2")
    out = s.act("I want to be in a forest!")
    assert s.pos() == {"x": 3, "y": 3, "depth": 0}
    assert "(3,3)" in out["story"]  # still where you started


def test_walking_changes_biome_eventually(monkeypatch):
    s = _Session(monkeypatch, "lost-3")
    start_biome = get_world_cell(s.act("look")["game_data"], 3, 3)["biome"]
    seen = {start_biome}
    for i in range(48):
        out = s.act("go east")
        pos = out["game_data"]["player_pos"]
        seen.add(get_world_cell(out["game_data"], pos["x"], pos["y"])["biome"])
        if len(seen) > 1:
            break
    assert len(seen) > 1, "walked 48 cells without leaving the starting biome"


def test_story_biome_tracks_travel(monkeypatch):
    s = _Session(monkeypatch, "lost-4")
    s.act("go east")
    s.act("go east")
    out = s.act("where am I now?")
    pos = out["game_data"]["player_pos"]
    assert pos == {"x": 5, "y": 3, "depth": 0}
    assert get_world_cell(out["game_data"], 5, 3)["biome"] in out["story"]


# ── Walking / borders /_negative coords ──

def test_go_north_three_times(monkeypatch):
    s = _Session(monkeypatch, "walker-1")
    s.act("go north")
    s.act("head north")
    out = s.act("walk north")
    assert out["game_data"]["player_pos"] == {"x": 3, "y": 0, "depth": 0}
    gd = out["game_data"]
    assert get_world_cell(gd, 3, 3)["explored"] is True
    assert get_world_cell(gd, 3, 0)["explored"] is True


def test_bare_direction_word_moves(monkeypatch):
    s = _Session(monkeypatch, "walker-2")
    assert s.act("North")["game_data"]["player_pos"] == {"x": 3, "y": 2, "depth": 0}
    assert s.act("w")["game_data"]["player_pos"] == {"x": 3, "y": 2, "depth": 0}  # bare 'w' is not a move


def test_case_insensitive_move(monkeypatch):
    s = _Session(monkeypatch, "walker-3")
    assert s.act("GO WEST")["game_data"]["player_pos"] == {"x": 2, "y": 3, "depth": 0}


def test_border_expansion_grows_window(monkeypatch):
    s = _Session(monkeypatch, "walker-4")
    out = None
    for _ in range(3):
        out = s.act("go north")
    assert len(out["game_data"]["grid"]) == 8
    assert out["game_data"]["origin"] == {"x": 0, "y": -2}
    assert any("expanded" in line for line in out["tool_results"])


def test_negative_coords_survive(monkeypatch):
    s = _Session(monkeypatch, "walker-5")
    for _ in range(4):
        s.act("go west")
    pos = s.pos()
    assert pos["x"] == -1
    cell = get_world_cell(s.saved()["game_data"], -1, 3)
    assert (cell["x"], cell["y"]) == (-1, 3) and cell["explored"] is True


def test_go_there_and_back_same_place(monkeypatch):
    s = _Session(monkeypatch, "walker-6")
    home = copy.deepcopy(get_world_cell(s.act("look")["game_data"], 3, 3))
    s.act("go east")
    back = s.act("go west")["game_data"]
    cell = get_world_cell(back, 3, 3)
    assert cell["biome"] == home["biome"] and cell["enemies"] == home["enemies"]


def test_gibberish_prompt_is_safe(monkeypatch):
    s = _Session(monkeypatch, "walker-7")
    out = s.act("asdf qwer zxcv blorpo")
    assert out["story"] and s.pos() == {"x": 3, "y": 3, "depth": 0}
    assert len(out["game_data"]["grid"]) == 6


def test_empty_action_look_is_quiet(monkeypatch):
    s = _Session(monkeypatch, "walker-8")
    out = s.act("look around")
    assert out["tool_results"] == [] or all("moved" not in t and "expanded" not in t for t in out["tool_results"])
    assert len(out["game_data"]["grid"]) == 6


# ── Persistence / sessions ──

def test_two_players_isolated_worlds(monkeypatch):
    a = _Session(monkeypatch, "sid-A")
    b = _Session(monkeypatch, "sid-B")
    ga, gb = a.act("look")["game_data"], b.act("look")["game_data"]
    assert ga["world_seed"] != gb["world_seed"]
    assert ga["grid"] != gb["grid"]
    a.act("go north")
    assert b.pos() == {"x": 3, "y": 3, "depth": 0}


def test_same_sid_rebuilds_same_world(monkeypatch):
    first = _Session(monkeypatch, "sid-same").act("look")["game_data"]["grid"]
    second = _Session(monkeypatch, "sid-same").act("look")["game_data"]["grid"]
    assert first == second


def test_chat_log_and_context_grow(monkeypatch):
    s = _Session(monkeypatch, "talker-1")
    s.act("hi")
    s.act("go east")
    out = s.act("attack the wolf")
    saved = s.saved()
    assert len(saved["chat_log"]) >= 3
    assert saved["context"] and "attack" in saved["context"]


def test_counter_counts_every_turn(monkeypatch):
    s = _Session(monkeypatch, "talker-2")
    for i in range(4):
        s.act(f"turn {i}")
    assert s.games.counters["talker-2"] == 4


def test_output_cache_holds_latest_story(monkeypatch):
    s = _Session(monkeypatch, "talker-3")
    s.act("hello")
    out = s.act("attack the orc")
    cached = s.out_client.data["talker-3"]
    assert cached["story"] == out["story"] and "orc" in cached["story"].lower()
    assert cached["game_data"]["player_pos"]["x"] == 3


def test_ttl_refreshed_on_save(monkeypatch):
    s = _Session(monkeypatch, "talker-4")
    s.act("hi")
    assert ("talker-4", 3600) in s.games.expires


def test_five_turn_mixed_playthrough(monkeypatch):
    s = _Session(monkeypatch, "campaign-1")
    s.act("where am I?")
    s.act("go east")
    s.act("slay the skeleton with my sword")
    s.act("go north")
    out = s.act("look around")
    gd = out["game_data"]
    assert gd["player_pos"] == {"x": 4, "y": 2, "depth": 0}
    assert len(gd.get("monsters", [])) >= 1
    assert s.games.counters["campaign-1"] == 5
    assert len(s.saved()["chat_log"]) >= 5


# ── Direct graph wiring (no orchestrator) ──

def _direct_state(monkeypatch, sid, prompt):
    _patch_offline(monkeypatch)
    from rpg_ai_server.redis.output_cache import OutputCache as _OC
    orch = GameOrchestrator(_OC(FakeOutputClient()), GameStateManager(FakeGamesClient()), worker_id="w")
    return orch._build_initial_state(GameRequest(uuid=sid, prompt=prompt))


def test_graph_routes_lore_to_search(monkeypatch):
    _patch_offline(monkeypatch)
    cache = OutputCache(FakeOutputClient())
    graph = gv2.build_game_graph_v2(cache).compile()
    out = _run(graph.ainvoke(
        _direct_state(monkeypatch, "lore-1", "tell me lore about dragons"),
        config={"recursion_limit": 60}))
    assert "dragon" in out["search_results"]
    assert any(t.get("tool") == "search" for t in out["router_trace"])
    assert out["game_output"]["story"]


def test_graph_worldgen_runs_before_mechanics(monkeypatch):
    _patch_offline(monkeypatch)
    cache = OutputCache(FakeOutputClient())
    graph = gv2.build_game_graph_v2(cache).compile()
    out = _run(graph.ainvoke(
        _direct_state(monkeypatch, "order-1", "go east and slay the goblin"),
        config={"recursion_limit": 60}))
    assert out["game_data"]["player_pos"] == {"x": 4, "y": 3, "depth": 0}
    texts = out["tool_results"]
    assert any("moved to (4,3)" in t for t in texts)
    assert any("damage: attack" in t for t in texts)


def test_graph_regenerates_far_cell_identically(monkeypatch):
    _patch_offline(monkeypatch)
    a = _direct_state(monkeypatch, "regen-1", "look")
    b = _direct_state(monkeypatch, "regen-1", "look")
    assert (get_world_cell(a["game_data"], 40, -17) ==
            get_world_cell(b["game_data"], 40, -17) ==
            generate_cell("regen-1", 40, -17))
