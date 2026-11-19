"""Compatibility facade — mock chat server moved into scripts/mock_chat/.

All public names are re-exported unchanged; existing imports and callers stay valid.
"""
from __future__ import annotations

from .mock_chat.client import MimicOpenRouterClient, install_mimic
from .mock_chat.cli import _print_story, _run, _repl, main
from .mock_chat.common import (
    ROOT, STATE_DIR, DEFAULT_SID, _MONSTERS, _seconds, _envelope, _when_true,
    MimicOptions,
)
from .mock_chat.session import MockState, MockSession

__all__ = [
    "ROOT", "STATE_DIR", "DEFAULT_SID", "MimicOptions", "MimicOpenRouterClient",
    "install_mimic", "MockState", "MockSession", "main", "_MONSTERS", "_seconds",
    "_envelope", "_when_true", "_print_story", "_run", "_repl",
]

if __name__ == "__main__":
    raise SystemExit(main())
