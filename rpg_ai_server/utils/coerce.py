from __future__ import annotations

"""Tiny coercions the whole pipeline repeats: dict-or-model state fields,
defensive ints, stat reads. One home so nodes stay short."""

from typing import Any


def to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def clamp_int(v: Any, lo: int, hi: int, default: int = 0) -> int:
    return max(lo, min(hi, to_int(v, default)))


def as_dict(obj: Any) -> Any:
    """Pydantic model -> dict; dicts (turn 2+ Redis round-trips) pass through."""
    if obj is None:
        return None
    return obj.model_dump() if hasattr(obj, "model_dump") else obj


def stat_of(stats: Any, name: str, default: Any = 0) -> Any:
    """Read a stat from a CharacterStats model or a plain (persisted) dict."""
    if isinstance(stats, dict):
        return stats.get(name, default)
    return getattr(stats, name, default)


def stat_int(stats: Any, name: str, default: int = 0) -> int:
    val = stat_of(stats, name, default)
    return to_int(val if val is not None else default, default)


def model_list(items: Any) -> list:
    """Serialize a list of models-or-dicts (inventory/skills/relationships)."""
    return [as_dict(i) for i in (items or [])]


def entry_name(entry: Any) -> str:
    if isinstance(entry, dict):
        return str(entry.get("name", ""))
    return str(getattr(entry, "name", ""))


def entry_level(entry: Any, default: int = 1) -> int:
    if isinstance(entry, dict):
        return to_int(entry.get("level", default), default)
    return to_int(getattr(entry, "level", default), default)


def labeled(entry: Any) -> str:
    """'name + type' search string for skill matching."""
    if isinstance(entry, dict):
        return f"{entry.get('name', '')} {entry.get('skill_type', '')}".lower()
    return f"{getattr(entry, 'name', '')} {getattr(entry, 'skill_type', '')}".lower()


