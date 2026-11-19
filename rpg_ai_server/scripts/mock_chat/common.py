"""Shared constants, envelope helpers and mimic options for the offline chat."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict

from . import ROOT, _TESTS_DIR

STATE_DIR = ROOT / ".mock-state"
DEFAULT_SID = "mock-chat"

_MONSTERS = ("goblin", "dragon", "wolf", "skeleton", "orc", "spider", "troll",
             "ogre", "rat", "bandit", "giant", "bandit leader", "goblin raider")

def _seconds() -> float:
    return time.time()

def _envelope(content: str, model: str, call: int, in_tok: int, out_tok: int) -> Dict[str, Any]:
    return {
        "id": f"chatcmpl-mimic-{call:03}",
        "object": "chat.completion",
        "created": int(_seconds()),
        "model": model,
        "usage": {
            "prompt_tokens": in_tok,
            "completion_tokens": out_tok,
            "total_tokens": in_tok + out_tok,
        },
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
    }

def _when_true(low: str, needles: tuple[str, ...]) -> bool:
    return any(n in low for n in needles)

@dataclass
class MimicOptions:
    """Tunable knobs for the fake OpenRouter-compatible model."""

    use_search: bool = False
    keep_images: bool = False
    talkative: bool = True
