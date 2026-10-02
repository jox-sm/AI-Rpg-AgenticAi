"""Atomic Redis tests: Lua-first wiring + safe fallbacks. No server needed.

Stubs stand in for Upstash: _client is set directly so connect() is a no-op,
and _eval_lua is either recorded (EVAL path) or forced to raise (fallback).
"""

import asyncio
import json

from rpg_ai_server.redis.client import GamesRedisClient, InputRedisClient


def _run(coro):
    return asyncio.run(coro)


class _Stub:
    def __init__(self, **behaviors):
        self.calls = []
        self.__dict__.update(behaviors)

    async def _missing(self, *a, **k):
        raise AssertionError("unexpected Redis call")


def _games_with(stub):
    c = GamesRedisClient()
    c._client = stub
    return c


def test_pop_delayed_is_single_eval_round_trip():
    seen = {}

    class S(_Stub):
        async def eval(self, script, keys=None, args=None):
            seen["script"] = script
            seen["keys"] = keys
            assert "ZRANGEBYSCORE" in script and "ZREMRANGEBYSCORE" in script
            return [json.dumps({"uuid": "a"}), json.dumps({"uuid": "b"})]

    c = InputRedisClient()
    c._client = S()
    out = _run(c.pop_delayed_due(123.0))
    assert [i["uuid"] for i in out] == ["a", "b"]
    assert seen["keys"] == ["input:queue:delayed"]


def test_pop_delayed_fallback_skips_poison():
    class S(_Stub):
        async def eval(self, *a, **k):
            raise RuntimeError("EVALREADONLY (cluster)")

        async def zrangebyscore(self, k, lo, hi):
            return [json.dumps({"uuid": "good"}), "{not-json"]

        async def zremrangebyscore(self, k, lo, hi):
            self.calls.append(("zrem", k))
            return 2

    c = InputRedisClient()
    c._client = S()
    out = _run(c.pop_delayed_due(9.0))
    assert out == [{"uuid": "good"}]  # poison skipped, drain not aborted
    assert c._client.calls == [("zrem", "input:queue:delayed")]


def test_release_lock_compare_and_delete():
    class S(_Stub):
        def __init__(self, ret):
            self.ret = ret

        async def eval(self, script, keys=None, args=None):
            assert "GET" in script and "DEL" in script
            assert keys == ["games:u:lock"] and args == ["w1"]
            return self.ret

    assert _run(_games_with(S(1)).release_lock("u", "w1")) is True
    assert _run(_games_with(S(0)).release_lock("u", "w1")) is False


def test_release_lock_fallback_rejects_stale_owner():
    # Lock expired and worker w2 acquired it; w1's delayed release must NOT delete.
    class S(_Stub):
        async def eval(self, *a, **k):
            raise RuntimeError("no eval")

        async def get(self, k):
            return "w2"

        async def delete(self, k):
            raise AssertionError("stale owner deleted live lock!")

    assert _run(_games_with(S()).release_lock("u", "w1")) is False


def test_refresh_lock_compare_and_expire():
    class S(_Stub):
        def __init__(self, ret):
            self.ret = ret

        async def eval(self, script, keys=None, args=None):
            assert "GET" in script and "EXPIRE" in script
            assert keys == ["games:u:lock"] and args[1] == "30"
            assert args[0] in ("w1", "intruder")
            return self.ret

    assert _run(_games_with(S(1)).refresh_lock("u", "w1")) is True
    assert _run(_games_with(S(0)).refresh_lock("u", "intruder")) is False


def test_touch_game_keys_expires_both():
    seen = {}

    class S(_Stub):
        async def eval(self, script, keys=None, args=None):
            seen["keys"] = keys
            assert "EXPIRE" in script
            return 1

    assert _run(_games_with(S()).touch_game_keys("u", 3600)) is True
    assert seen["keys"] == ["games:u:state", "games:u:counter"]


def test_set_counter_sets_ttl():
    seen = {}

    class S(_Stub):
        async def set(self, k, v, ex=None, **kw):
            seen.update(key=k, val=v, ex=ex)
            return True

    assert _run(_games_with(S()).set_counter("u", 0)) is True
    assert seen == {"key": "games:u:counter", "val": "0", "ex": 3600}
