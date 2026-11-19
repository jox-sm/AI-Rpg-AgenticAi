"""Compatibility facade — Redis clients moved into redis/clients/.

Importing this module still applies the httpx legacy-TLS patch first (via
clients.tls) before upstash_redis is imported, preserving startup behavior.
"""
from upstash_redis import AsyncRedis as UpstashRedis

from .clients.base import RedisClient
from .clients.games_client import GamesRedisClient
from .clients.input_client import InputRedisClient
from .clients.output_client import OutputRedisClient
from .clients.tls import (
    _LegacyTLSAsyncClient, _LegacyTLSClient, _legacy_ssl_context,
    _patch_httpx_legacy_tls,
)

__all__ = [
    "RedisClient", "InputRedisClient", "OutputRedisClient", "GamesRedisClient",
    "UpstashRedis", "_patch_httpx_legacy_tls", "_legacy_ssl_context",
    "_LegacyTLSClient", "_LegacyTLSAsyncClient",
]
