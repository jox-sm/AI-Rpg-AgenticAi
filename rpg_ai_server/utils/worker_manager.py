from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


_WORKERS: list[dict] | None = None


def _load_workers() -> list[dict]:
    global _WORKERS
    if _WORKERS is None:
        path = Path(__file__).resolve().parent.parent.parent / "items-db" / "workers.json"
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            _WORKERS = [w for w in raw if isinstance(w, dict) and "id" in w]
        else:
            _WORKERS = []
    return _WORKERS


def get_all_workers() -> list[dict]:
    return list(_load_workers())


def get_worker(worker_id: str) -> dict | None:
    for w in _load_workers():
        if w["id"] == worker_id:
            return dict(w)
    return None


def find_workers_at_station(station_name: str) -> list[dict]:
    station_lower = station_name.lower().strip()
    result = []
    for w in _load_workers():
        if w.get("station", "").lower().strip() == station_lower:
            result.append(dict(w))
    return result


def find_workers_at_location(location_name: str) -> list[dict]:
    location_lower = location_name.lower().strip()
    result = []
    for w in _load_workers():
        locs = [loc.lower().strip() for loc in w.get("locations", [])]
        if any(location_lower in loc or loc in location_lower for loc in locs):
            result.append(dict(w))
    return result


def find_workers_for_skill(skill_key: str) -> list[dict]:
    skill_lower = skill_key.lower().strip()
    result = []
    for w in _load_workers():
        for mastery_key in w.get("mastery", {}):
            if mastery_key.lower().strip() == skill_lower:
                result.append(dict(w))
                break
    return result


def worker_has_skill(worker: dict, skill_key: str) -> bool:
    return skill_key.lower().strip() in {k.lower().strip() for k in worker.get("mastery", {})}


def worker_skill_level(worker: dict, skill_key: str) -> int:
    for k, v in worker.get("mastery", {}).items():
        if k.lower().strip() == skill_key.lower().strip():
            return int(v)
    return 0


def calculate_worker_cost(worker: dict, difficulty: str = "normal", quantity: int = 1) -> int:
    base = worker.get("cost_per_attempt", 50)
    diff_mult = {"trivial": 0.5, "easy": 0.75, "normal": 1.0, "hard": 1.5, "very_hard": 2.0, "legendary": 3.0}
    mult = diff_mult.get(difficulty, 1.0)
    return int(base * mult * quantity)


def format_worker_option(worker: dict, skill_key: str) -> dict:
    level = worker_skill_level(worker, skill_key)
    return {
        "id": worker["id"],
        "name": worker["name"],
        "title": worker.get("title", ""),
        "station": worker.get("station", ""),
        f"mastery_{skill_key}_level": level,
        "cost_per_attempt": worker.get("cost_per_attempt", 0),
        "currency": worker.get("currency", "gold"),
        "description": worker.get("description", ""),
        "personality": worker.get("personality", ""),
    }


def can_afford_worker(gold: int, cost: int) -> bool:
    return gold >= cost


def format_choice_message(
    player_level: int,
    worker_options: list[dict],
    skill_key: str,
    item_name: str,
    player_location: str,
) -> str:
    lines = [f"Location: {player_location}"]
    lines.append(f"Your {skill_key} mastery: Lv{player_level}")
    lines.append("")
    lines.append("Available workers:")

    for w in worker_options:
        wlvl = worker_skill_level(w, skill_key)
        cost = w.get("cost_per_attempt", 0)
        lines.append(f"  [{w['id']}] {w['name']} ({w.get('title', '')}) — {skill_key} Lv{wlvl}, {cost} gold each")
        lines.append(f"         {w.get('description', '')}")

    lines.append("")
    lines.append("Choices:")
    lines.append("  1. Do it yourself (uses your mastery, no cost)")
    lines.append(f"  2. Hire a worker (uses worker's mastery, costs gold)")
    lines.append("")
    lines.append("To craft yourself, use: use_skill")
    lines.append("To hire, use: hire_worker with the worker's id")

    return "\n".join(lines)


def worker_mastery_check(
    worker_id: str,
    skill_key: str,
    difficulty: str = "normal",
    stat_bonus: int = 0,
) -> dict | None:
    worker = get_worker(worker_id)
    if not worker:
        return None
    if not worker_has_skill(worker, skill_key):
        return None

    from ..utils.mastery import mastery_check

    level = worker_skill_level(worker, skill_key)
    result = mastery_check(level, skill_key, difficulty, stat_bonus)
    result["worker_id"] = worker_id
    result["worker_name"] = worker["name"]
    return result
