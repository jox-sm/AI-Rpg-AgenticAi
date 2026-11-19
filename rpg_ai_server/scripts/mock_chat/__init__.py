"""Offline mock OpenRouter chat package (split from scripts/mock_openrouter_chat.py).

Runs the same sys.path bootstrap the original script ran before importing
``tests.fakes`` and the game graph; the file is one package deeper now.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Expose the offline test fakes so one script covers Redis/Upstash substitutes.
_TESTS_DIR = ROOT / "tests"
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))
