import asyncio

import pytest

from rpg_ai_server.redis.client import GamesRedisClient


def _run(coro):
    return asyncio.run(coro)


class _SdkBehavior:
    """Stubs the upstash_redis SDK conventions:

    - set(..., nx=True) returns True on success, False when key exists
      (NOT None — that is the upstash-redis contract; redis-py returns None).
    """

    def __init__(self):
        self.set_calls = []
        self.lock_value = None

    async def set(self, key, value, nx=False, ex=None):
        self.set_calls.append((key, value, nx, ex))
        if nx and self.lock_value is not None:
            return False
        self.lock_value = value
        return True

    async def get(self, key):
        return self.lock_value

    async def delete(self, key):
        removed = self.lock_value is not None
        self.lock_value = None
        return 1 if removed else 0

    async def expire(self, key, ttl):
        return True

    async def close(self):
        pass


@pytest.mark.anyio
async def test_acquire_lock_rejects_second_worker_on_sdk_false(monkeypatch):
    client = GamesRedisClient()
    sdk = _SdkBehavior()
    client._client = sdk

    first = await client.acquire_lock("u1", "worker-a")
    second = await client.acquire_lock("u1", "worker-b")
    assert first is True
    assert second is False

    released = await client.release_lock("u1", "worker-a")
    assert released is True
    reacquired = await client.acquire_lock("u1", "worker-b")
    assert reacquired is True


@pytest.mark.anyio
async def test_release_lock_rejects_wrong_worker(monkeypatch):
    client = GamesRedisClient()
    sdk = _SdkBehavior()
    client._client = sdk

    await client.acquire_lock("u1", "worker-a")
    assert await client.release_lock("u1", "intruder") is False
    assert await client.release_lock("u1", "worker-a") is True