from __future__ import annotations

import json
import ssl
from typing import Any, Dict, Optional, List

import httpx

from ...config.settings import settings
from ...utils.logger import logger


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
