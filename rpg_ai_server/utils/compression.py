from __future__ import annotations

import base64
import gzip
from typing import Optional


def compress_text(text: str) -> str:
    compressed = gzip.compress(text.encode("utf-8"))
    return base64.b64encode(compressed).decode("ascii")


def decompress_text(data: str) -> Optional[str]:
    try:
        raw = base64.b64decode(data)
        return gzip.decompress(raw).decode("utf-8")
    except Exception:
        return None
