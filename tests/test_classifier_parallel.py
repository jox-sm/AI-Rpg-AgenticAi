"""Classifier + Node4-parallel tests. Deterministic paths only; LLM stubbed."""

import asyncio
import json

import rpg_ai_server.agents.classifier as clf
from rpg_ai_server.agents.classifier import classifier_node, deterministic_pass
from rpg_ai_server.agents.node4_parallel import _ORDER, node4_parallel


def _run(coro):
    return asyncio.run(coro)


def test_deterministic_image_short_circuits_llm(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("LLM must not be called on deterministic path")

    monkeypatch.setattr(clf, "get_openrouter_direct", boom)
    out = _run(classifier_node({"prompt": "look", "images": {"a": {}}}))
    assert out["decision_report"]["needs_image"] is True
    assert out["decision_report"]["confidence"] == 0.95
    assert out["needs_image_processing"] is True


def test_deterministic_plain_prompt_skips_llm_when_no_lore(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("LLM must not be called")

    monkeypatch.setattr(clf, "get_openrouter_direct", boom)
    assert deterministic_pass("hello there", False) is None


def test_llm_path_parses_report_and_applies_confidence_floor(monkeypatch):
    calls = {}

    class FakeDirect:
        async def chat_completion(self, model=None, messages=None, **kw):
            calls["n"] = len(messages)
            assert "strict JSON" in messages[0]["content"]
            assert kw.get("response_format") == {"type": "json_object"}
            return {"choices": [{"message": {"content": json.dumps({
                "intent": "attack", "target": "goblin", "monster_move": "defend",
                "buffs": ["flank"], "debuffs": [], "needs_search": True,
                "search_query": "goblin lore", "confidence": 0.2,  # low → no search
                "reason": "test",
            })}}]}

    monkeypatch.setattr(clf, "get_openrouter_direct", lambda: FakeDirect())
    out = _run(classifier_node({"prompt": "slay the beast", "images": {}}))
    rep = out["decision_report"]
    assert rep["intent"] == "attack" and rep["target"] == "goblin"
    assert rep["needs_search"] is False  # confidence floor overrode True
    assert calls["n"] == 2


def test_classifier_total_failure_returns_safe_defaults(monkeypatch):
    class BoomDirect:
        async def chat_completion(self, *a, **k):
            raise RuntimeError("openrouter 429")

    monkeypatch.setattr(clf, "get_openrouter_direct", lambda: BoomDirect())
    out = _run(classifier_node({"prompt": "zzz", "images": {}}))
    assert out["decision_report"]["confidence"] == 0.0
    assert out["needs_search"] is False


def test_node4_parallel_merges_in_fixed_order_with_turn_id():
    s = {"uuid": "u", "turn_id": "u:abc", "prompt": "attack",
         "decision_report": {"intent": "attack", "target": "rat", "monster_move": "flee"},
         "character_stats": {"level": 3}, "skills": [{"cooldown": 2}],
         "inventory": [1, 2], "relationships": [], "grid_data": {}}
    out = _run(node4_parallel(s))
    assert out["turn_id"] == "u:abc"
    assert out["tool_results"][0].startswith("turn=u:abc mechanics:")
    body = out["tool_results"][0]
    assert body.index("- dice:") < body.index("- damage:") < body.index("- stats:")
    assert "monster:flee" in body and "target:rat" in body
    assert out["skills"] == [{"cooldown": 1}]  # overwrite, not append
    assert out["inventory"] == [1, 2]


def test_node4_parallel_isolates_subnode_crash(monkeypatch):
    import rpg_ai_server.agents.node4_parallel as n4

    async def boom(snap):
        raise RuntimeError("dice table on fire")

    monkeypatch.setitem(n4._SUBNODES, "dice", boom)
    out = _run(node4_parallel({"uuid": "u", "turn_id": "t", "prompt": "",
                               "skills": [], "inventory": []}))
    assert "- dice: error dice table on fire" in out["tool_results"][0]
    assert "- damage:" in out["tool_results"][0]  # siblings unaffected
    assert set(out["mechanics_patches"]) == set(_ORDER)
