"""Contract tests: fakes must mirror the real clients' public surface.

These tests fail when production code gains a method (e.g. touch_game_keys)
but tests/fakes.py is not updated — the exact drift that hid P03/P04.
"""

from rpg_ai_server.redis import client as real
from tests import fakes


def _public_methods(cls):
    # Include inherited helpers (set_json/keys/dbsize/... come from RedisClient).
    methods = set()
    for klass in cls.__mro__:
        methods.update(
            name
            for name, fn in klass.__dict__.items()
            if callable(fn) and not name.startswith("_") and name not in ("connect", "disconnect", "client")
        )
    return methods


# Domain methods production code actually calls — fakes must cover exactly these.
GAMES_DOMAIN = {"hset", "hget", "hgetall", "hdel", "incr", "set_counter", "expire",
                "acquire_lock", "release_lock", "refresh_lock", "touch_game_keys"}
INPUT_DOMAIN = {"pop_request", "push_request", "queue_length", "push_delayed",
                "pop_delayed_due", "push_dead", "set_heartbeat",
                "get_heartbeat", "get_all_keys"}
OUTPUT_DOMAIN = {"push_result", "count", "get_json"}


def test_games_fake_covers_real_surface():
    fake = _public_methods(fakes.FakeGamesClient)
    assert GAMES_DOMAIN <= fake, f"missing: {sorted(GAMES_DOMAIN - fake)}"
    assert GAMES_DOMAIN <= _public_methods(real.GamesRedisClient)


def test_input_fake_covers_real_surface():
    fake = _public_methods(fakes.FakeInputClient)
    assert INPUT_DOMAIN <= fake, f"missing: {sorted(INPUT_DOMAIN - fake)}"
    assert INPUT_DOMAIN <= _public_methods(real.InputRedisClient)


def test_output_fake_covers_real_surface():
    fake = _public_methods(fakes.FakeOutputClient)
    assert OUTPUT_DOMAIN <= fake, f"missing: {sorted(OUTPUT_DOMAIN - fake)}"
    assert OUTPUT_DOMAIN <= _public_methods(real.OutputRedisClient)


def test_set_counter_accepts_ttl_kwarg():
    import asyncio

    async def go():
        for cls in (fakes.FakeGamesClient,):
            c = cls()
            assert await c.set_counter("u", 3, ttl=60) is True
            assert await c.touch_game_keys("u", 60) is True

    asyncio.run(go())


def test_load_state_treats_empty_dict_as_missing():
    """Real Upstash hgetall returns {} for missing keys (not None)."""
    import asyncio

    from rpg_ai_server.redis.game_state import GameStateManager

    class EmptyHash:
        async def hgetall(self, uuid):
            return {}

    async def go():
        mgr = GameStateManager(EmptyHash())
        assert await mgr.load_state("nope") is None

    asyncio.run(go())
