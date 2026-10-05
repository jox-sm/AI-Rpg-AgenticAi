import asyncio
import inspect

from langgraph.errors import GraphRecursionError

from rpg_ai_server.config.settings import settings
from rpg_ai_server.engine.orchestrator import GRACEFUL_ERROR_STORY, GameOrchestrator


def _run(coro):
    return asyncio.run(coro)


class StubGraph:
    def __init__(self, behavior):
        self.behavior = behavior
        self.last_config = None

    async def ainvoke(self, state, config=None):
        self.last_config = config
        out = self.behavior(state, config)
        if inspect.isawaitable(out):
            return await out
        return out


class StubStateManager:
    def __init__(self, existing=None):
        self.locked = set()
        self.refreshes = 0
        self.saved = []
        self.drained = []
        self.initial_saved = []
        self.existing = existing

    async def acquire_lock(self, uuid, worker_id, ttl=None):
        if uuid in self.locked:
            return False
        self.locked.add(uuid)
        return True

    async def release_lock(self, uuid, worker_id):
        self.locked.discard(uuid)
        return True

    async def refresh_lock(self, uuid, worker_id, ttl=None):
        self.refreshes += 1
        return uuid in self.locked

    async def load_state(self, uuid):
        return self.existing

    async def save_initial_state(self, uuid, game_data, story="", chat_log=None, context=""):
        self.initial_saved.append((uuid, game_data))

    async def save_state(self, uuid, state, fields):
        self.saved.append((uuid, state, fields))

    async def try_drain(self, uuid, story, is_major=False):
        self.drained.append((uuid, story))
        return True


class StubRequest:
    def __init__(self, uuid="u1", prompt="Fight the dragon", data=None, images=None):
        self.uuid = uuid
        self.prompt = prompt
        self.data = data or {}
        self.images = images or []


MINIMAL_STATE = {
    "uuid": "u1",
    "prompt": "",
    "input_data": {},
    "game_data": {},
    "images": {},
    "grid_data": {},
    "re_description_data": None,
    "context_summary": None,
    "character_stats": None,
    "skills": [],
    "inventory": [],
    "relationships": [],
    "story_output": "",
    "decision": None,
    "needs_search": False,
    "needs_image_processing": False,
    "needs_re_description": False,
    "processed": False,
    "error": None,
    "search_results": "",
    "tool_results": [],
    "game_output": None,
    "conditional_passes": 0,
    "remaining_steps": settings.app.loop_recursion_limit,
    "__next__": "node4_tool_agent",
}


def _orch(stub_mgr, behavior):
    orch = GameOrchestrator(output_cache=None, game_state_mgr=stub_mgr, worker_id="w1")
    orch.compiled_graph = StubGraph(behavior)
    orch._build_initial_state = lambda req: MINIMAL_STATE
    return orch


def _ok_output():
    return {"game_output": {"story": "The dragon was slain!", "game_data": {"hp": 42}}}


def test_process_request_success_flow():
    stub = StubStateManager()
    orch = _orch(stub, lambda state, config: _ok_output())

    out = _run(orch.process_request(StubRequest()))

    assert out["story"] == "The dragon was slain!"
    assert stub.locked == set()
    assert len(stub.saved) == 1
    uuid, state, fields = stub.saved[0]
    assert uuid == "u1"
    assert "context_summary" in fields and "decision" in fields
    assert len(stub.drained) == 1
    assert stub.drained[0][1] == "The dragon was slain!"


def test_process_request_persists_context_summary():
    stub = StubStateManager()

    def behavior(state, config):
        state = dict(state)
        state["context_summary"] = {"events": ["dragon"]}
        state["game_output"] = {"story": "done", "game_data": {}}
        return state

    orch = _orch(stub, behavior)
    _run(orch.process_request(StubRequest()))
    saved_state = stub.saved[0][1]
    assert saved_state["context_summary"] == {"events": ["dragon"]}


def test_process_request_uses_existing_state():
    stub = StubStateManager(existing={"story": "old story"})
    orch = _orch(stub, lambda state, config: _ok_output())
    _run(orch.process_request(StubRequest()))
    assert not stub.initial_saved
    assert len(stub.saved) == 1


def test_process_request_saves_initial_state_for_new_game():
    stub = StubStateManager()
    orch = _orch(stub, lambda state, config: _ok_output())
    _run(orch.process_request(StubRequest()))
    assert len(stub.initial_saved) == 1


def test_lock_not_acquired_returns_none():
    stub = StubStateManager()
    stub.locked.add("u1")
    orch = _orch(stub, lambda state, config: _ok_output())
    assert _run(orch.process_request(StubRequest())) is None


def test_graph_recursion_error_is_graceful():
    stub = StubStateManager()

    def boom(state, config):
        raise GraphRecursionError("Recursion limit of 60 reached")

    orch = _orch(stub, boom)
    out = _run(orch.process_request(StubRequest()))
    assert out["story"] == GRACEFUL_ERROR_STORY
    assert "Recursion limit" not in out["story"]
    assert stub.locked == set()


def test_generic_error_does_not_leak_message():
    stub = StubStateManager()

    def boom(state, config):
        raise RuntimeError("super-secret internal token leak")

    orch = _orch(stub, boom)
    out = _run(orch.process_request(StubRequest()))
    assert out["error"] == "RuntimeError"
    assert "super-secret" not in out["story"]
    assert "super-secret" not in out["error"]
    assert stub.locked == set()


def test_timeout_is_graceful(monkeypatch):
    monkeypatch.setattr(settings.app, "request_timeout_seconds", 0.05)
    stub = StubStateManager()

    async def slow(state, config):
        await asyncio.sleep(0.5)
        return _ok_output()

    orch = _orch(stub, slow)
    out = _run(orch.process_request(StubRequest()))
    assert out["story"] == GRACEFUL_ERROR_STORY
    assert out["error"] == "TimeoutError"
    assert stub.locked == set()


def test_recursion_limit_passed_to_graph():
    stub = StubStateManager()
    graph = StubGraph(lambda state, config: _ok_output())
    orch = _orch(stub, graph.behavior)
    orch.compiled_graph = graph
    _run(orch.process_request(StubRequest()))
    assert graph.last_config == {"recursion_limit": settings.app.loop_recursion_limit}


def test_lock_is_refreshed_during_long_run(monkeypatch):
    monkeypatch.setattr(settings.app, "lock_refresh_interval", 0.01)
    monkeypatch.setattr(settings.app, "request_timeout_seconds", 5.0)
    stub = StubStateManager()

    async def slowish(state, config):
        await asyncio.sleep(0.1)
        return _ok_output()

    orch = _orch(stub, slowish)
    _run(orch.process_request(StubRequest()))
    assert stub.refreshes >= 1
    assert stub.locked == set()


def test_process_request_persists_top_level_inventory():
    """Regression: inventory/skills lived only inside game_data copy and were
    lost on resume (top-level state reset to []). They must be saved as fields."""
    stub = StubStateManager()

    def behavior(state, config):
        state = dict(state)
        state["inventory"] = [{"item_id": "sword", "name": "Sword", "quantity": 1}]
        state["skills"] = [{"name": "Dodge", "skill_type": "defense"}]
        state["game_output"] = {"story": "done", "game_data": {}}
        return state

    orch = _orch(stub, behavior)
    _run(orch.process_request(StubRequest()))
    saved_state, fields = stub.saved[0][1], stub.saved[0][2]
    assert "inventory" in fields and "skills" in fields
    assert saved_state["inventory"] == [{"item_id": "sword", "name": "Sword", "quantity": 1}]
    assert saved_state["skills"] == [{"name": "Dodge", "skill_type": "defense"}]
