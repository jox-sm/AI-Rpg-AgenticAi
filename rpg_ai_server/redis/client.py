from __future__ import annotations

import json
import ssl
from typing import Any, Dict, Optional, List

import httpx

from ..config.settings import settings
from ..utils.logger import logger


def _patch_httpx_legacy_tls() -> None:
    """Upstash's edge requires legacy TLS renegotiation approval on pooled
    connections. Modern OpenSSL (3.0+) disables this by default, which makes
    long-lived SDK clients fail with UNSAFE_LEGACY_RENEGOTIATION_DISABLED.
    Replace httpx clients with subclasses that inject a default SSLContext
    with OP_LEGACY_SERVER_CONNECT (subclass keeps openai etc. subclassing
    httpx.Client working)."""
    if getattr(httpx, "Client", None) is _LegacyTLSClient:
        return
    httpx.Client = _LegacyTLSClient
    httpx.AsyncClient = _LegacyTLSAsyncClient


def _legacy_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
    return ctx


class _LegacyTLSClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        if kwargs.get("verify") is None:
            kwargs["verify"] = _legacy_ssl_context()
        super().__init__(*args, **kwargs)


class _LegacyTLSAsyncClient(httpx.AsyncClient):
    def __init__(self, *args, **kwargs):
        if kwargs.get("verify") is None:
            kwargs["verify"] = _legacy_ssl_context()
        super().__init__(*args, **kwargs)


_patch_httpx_legacy_tls()

from upstash_redis import AsyncRedis as UpstashRedis


class RedisClient:
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self._client: Optional[UpstashRedis] = None

    async def connect(self):
        if self._client is None:
            if not settings.redis.use_upstash:
                raise RuntimeError(
                    "Upstash Redis REST URL and token must be set in environment"
                )
            self._client = UpstashRedis(
                url=settings.redis.upstash_rest_url,
                token=settings.redis.upstash_rest_token,
            )
            logger.info(f"Connected to Upstash Redis (prefix={self.prefix})")

    async def disconnect(self):
        if self._client is None:
            return
        await self._client.close()
        self._client = None

    @property
    def client(self) -> UpstashRedis:
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}" if self.prefix else key

    async def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        ttl = ttl or settings.redis.ttl_seconds
        await self.connect()
        full_key = self._key(key)
        serialized = json.dumps(value)
        await self.client.set(full_key, serialized, ex=ttl)
        return True

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        await self.connect()
        full_key = self._key(key)
        data = await self.client.get(full_key)
        if data is None:
            return None
        return json.loads(data)

    async def delete(self, key: str) -> bool:
        await self.connect()
        full_key = self._key(key)
        result = await self.client.delete(full_key)
        return result > 0

    async def exists(self, key: str) -> bool:
        await self.connect()
        full_key = self._key(key)
        result = await self.client.exists(full_key)
        return result > 0

    async def keys(self, pattern: str = "*") -> List[str]:
        await self.connect()
        full_pattern = self._key(pattern) if self.prefix else pattern
        result = await self.client.keys(full_pattern)
        if self.prefix and result:
            prefix_len = len(self.prefix) + 1
            return [k[prefix_len:] for k in result]
        return result

    async def dbsize(self) -> int:
        await self.connect()
        if self.prefix:
            keys_list = await self.client.keys(self._key("*"))
            return len(keys_list)
        return await self.client.dbsize()

    async def memory_usage(self, key: str) -> Optional[int]:
        await self.connect()
        full_key = self._key(key)
        try:
            result = await self.client.execute("MEMORY", "USAGE", full_key)
            return result
        except Exception:
            return None

    async def info_section(self, section: str = "memory") -> Dict[str, Any]:
        await self.connect()
        try:
            raw = await self.client.execute("INFO", section)
            info: Dict[str, Any] = {}
            for line in raw.split("\n"):
                if ":" in line:
                    k, v = line.strip().split(":", 1)
                    try:
                        info[k] = int(v)
                    except ValueError:
                        info[k] = v
            return info
        except Exception:
            return {}

    async def memory_percent(self) -> float:
        info = await self.info_section("memory")
        used_memory = info.get("used_memory", 0)
        max_memory = info.get("maxmemory", 0)
        if max_memory == 0:
            return 0.0
        return (used_memory / max_memory) * 100.0


class InputRedisClient(RedisClient):
    def __init__(self):
        super().__init__(prefix="input")

    async def pop_request(self) -> Optional[Dict[str, Any]]:
        await self.connect()
        raw = await self.client.lpop(self._key("queue"))
        if raw is None:
            return None
        return json.loads(raw)

    async def push_request(self, uuid: str, data: Dict[str, Any]) -> bool:
        await self.connect()
        serialized = json.dumps(data)
        await self.client.rpush(self._key("queue"), serialized)
        return True

    async def queue_length(self) -> int:
        await self.connect()
        return await self.client.llen(self._key("queue"))

    async def push_delayed(self, item: Dict[str, Any], score: float) -> bool:
        await self.connect()
        serialized = json.dumps(item)
        await self.client.zadd(self._key("queue:delayed"), {serialized: score})
        return True

    async def pop_delayed_due(self, max_score: float) -> list[Dict[str, Any]]:
        await self.connect()
        key = self._key("queue:delayed")
        raw_items = await self.client.zrangebyscore(key, 0, max_score)
        if not raw_items:
            return []
        await self.client.zremrangebyscore(key, 0, max_score)
        return [json.loads(r) for r in raw_items]

    async def push_dead(self, item: Dict[str, Any]):
        await self.connect()
        serialized = json.dumps(item)
        score = item.get("timestamp", 0)
        await self.client.zadd(self._key("queue:dead"), {serialized: score})

    async def set_heartbeat(self, worker_id: str, game_uuid: str, ttl: int = 15) -> bool:
        await self.connect()
        await self.client.set(self._key(f"workers:{worker_id}:heartbeat"), game_uuid, ex=ttl)
        return True

    async def get_heartbeat(self, worker_id: str) -> Optional[str]:
        await self.connect()
        return await self.client.get(self._key(f"workers:{worker_id}:heartbeat"))

    async def get_all_keys(self) -> list[str]:
        return await self.keys("*")


class OutputRedisClient(RedisClient):
    def __init__(self):
        super().__init__(prefix="output")

    async def push_result(self, uuid: str, data: Dict[str, Any]) -> bool:
        return await self.set_json(uuid, data)

    async def count(self) -> int:
        return await self.dbsize()


class GamesRedisClient(RedisClient):
    def __init__(self):
        super().__init__(prefix="games")

    async def hset(self, uuid: str, field: str, value: str) -> bool:
        await self.connect()
        await self.client.hset(self._key(f"{uuid}:state"), field, value)
        return True

    async def hget(self, uuid: str, field: str) -> Optional[str]:
        await self.connect()
        return await self.client.hget(self._key(f"{uuid}:state"), field)

    async def hgetall(self, uuid: str) -> Optional[Dict[str, str]]:
        await self.connect()
        return await self.client.hgetall(self._key(f"{uuid}:state"))

    async def hdel(self, uuid: str, field: str) -> bool:
        await self.connect()
        result = await self.client.hdel(self._key(f"{uuid}:state"), field)
        return result > 0

    async def incr(self, uuid: str) -> int:
        await self.connect()
        return await self.client.incr(self._key(f"{uuid}:counter"))

    async def set_counter(self, uuid: str, value: int) -> bool:
        await self.connect()
        await self.client.set(self._key(f"{uuid}:counter"), str(value))
        return True

    async def expire(self, uuid: str, ttl: int) -> bool:
        await self.connect()
        result = await self.client.expire(self._key(f"{uuid}:state"), ttl)
        return result > 0

    async def acquire_lock(self, uuid: str, worker_id: str, ttl: int = 30) -> bool:
        await self.connect()
        result = await self.client.set(
            self._key(f"{uuid}:lock"), worker_id, nx=True, ex=ttl
        )
        return bool(result)

    async def release_lock(self, uuid: str, worker_id: str) -> bool:
        await self.connect()
        key = self._key(f"{uuid}:lock")
        current = await self.client.get(key)
        if current == worker_id:
            await self.client.delete(key)
            return True
        return False

    async def refresh_lock(self, uuid: str, worker_id: str, ttl: int = 30) -> bool:
        await self.connect()
        key = self._key(f"{uuid}:lock")
        current = await self.client.get(key)
        if current == worker_id:
            await self.client.expire(key, ttl)
            return True
        return False
