"""Shared Redis REST client: prefixing, JSON, Lua, admin helpers."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ...config.settings import settings
from ...utils.logger import logger
from .tls import _patch_httpx_legacy_tls  # noqa: F401 — patch fires before upstash import

from upstash_redis import AsyncRedis as UpstashRedis

class RedisClient:
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self._client: Optional[UpstashRedis] = None

    async def _eval_lua(self, script: str, keys: list[str], args: list[str]):
        """Run Lua atomically via EVAL; raise to let caller fall back if unsupported."""
        await self.connect()
        return await self.client.eval(script, keys=keys, args=args)

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
