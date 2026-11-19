"""Deterministic per-coordinate cell generation for the infinite world."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import (
    _FALLBACK_BIOME_NAMES, _ITEMS_DB, _db_lists, _pick, _region_biome_name,
    _seeded_rng,
)

def generate_cell(world_seed: str, wx: int, wy: int, _lists: Optional[Dict[str, List[Dict[str, Any]]]] = None,
                  scalar: float = 1.0) -> Dict[str, Any]:
    """Generate the one deterministic cell for world coordinate (wx, wy).

    ``scalar`` is the adaptive-difficulty signal (1.0x -> 4.0x): higher scalar
    packs more monsters into freshly generated cells (+2 per extra 1.0x).
    Stored cells are immutable afterwards, so revisits stay stable; only the
    frontier reflects the current scalar.
    """
    seed = world_seed or "world"
    rng = _seeded_rng(f"{seed}:{wx}:{wy}")
    try:
        density = max(1.0, min(4.0, float(scalar)))
    except (TypeError, ValueError):
        density = 1.0
    lists = _lists if _lists is not None else _db_lists()
    biomes = lists.get("biomes") or []
    biome_names = [b.get("name", "Unknown") for b in biomes if isinstance(b, dict) and b.get("name")] or list(_FALLBACK_BIOME_NAMES)
    biome_name = _region_biome_name(seed, wx, wy, biome_names)
    biome_data = next((b for b in biomes if isinstance(b, dict) and b.get("name") == biome_name), {})
    if not isinstance(biome_data, dict):
        biome_data = {}

    cell_weather = _pick(lists.get("weather") or [], rng, rng.randint(1, 2))
    cell_buildings = _pick(lists.get("buildings") or [], rng, rng.randint(0, 2))
    cell_npcs = _pick(lists.get("npcs") or [], rng, max(1, rng.randint(0, 3)))
    cell_events = _pick(lists.get("events") or [], rng, rng.randint(0, 1))
    all_enemies = lists.get("enemies") or []

    enemy_names = biome_data.get("Enemies", "") if isinstance(biome_data.get("Enemies", ""), str) else ""
    cell_enemies: List[Dict[str, Any]] = []
    if enemy_names:
        for e_name in [s.strip() for s in enemy_names.split(",") if s.strip()]:
            try:
                found = _ITEMS_DB.get_by_name(e_name)
            except Exception:
                found = None
            if found:
                cell_enemies.append(found)
    if not cell_enemies:
        cell_enemies = _pick(all_enemies, rng, rng.randint(1, 2))
    # Difficulty signal: scarier worlds pack more monsters per cell.
    extra = int((density - 1.0) * 2)
    if extra > 0:
        cell_enemies = list(cell_enemies) + _pick(all_enemies, rng, extra)

    from ...scripts.xp_loot import parse_level_range
    resources = biome_data.get("Resources", "")
    difficulty_min, difficulty_max = parse_level_range(biome_data.get("Difficulty Level", "1"))

    return {
        "x": wx,
        "y": wy,
        "biome": biome_name,
        "terrain": biome_data.get("Terrain Type", "Open field"),
        "temperature": biome_data.get("Temperature Range", ""),
        "humidity": biome_data.get("Humidity", ""),
        "weather": [w.get("name", "Clear") for w in cell_weather if isinstance(w, dict)],
        "resources": [r.strip() for r in resources.split(",") if r.strip()] if isinstance(resources, str) else [],
        "difficulty": {"min": difficulty_min, "max": difficulty_max},
        "buildings": [
            {"name": b.get("name", ""), "type": b.get("Type", ""), "size": b.get("Size", "")}
            for b in cell_buildings if isinstance(b, dict)
        ],
        "npcs": [
            {"name": n.get("name", ""), "role": n.get("Role", ""), "personality": n.get("Personality", "")}
            for n in cell_npcs if isinstance(n, dict)
        ],
        "enemies": [
            {"name": e.get("name", ""), "level": e.get("Level", difficulty_min)}
            for e in cell_enemies if isinstance(e, dict)
        ],
        "events": [e.get("name", "") for e in cell_events if isinstance(e, dict)],
        "factions": [f.get("name", "") for f in _pick(lists.get("factions") or [], rng, rng.randint(0, 2)) if isinstance(f, dict)],
        "explored": False,
        "features": [],
    }


def _valid_grid(grid: Any) -> bool:
    return (
        isinstance(grid, list) and len(grid) > 0
        and all(isinstance(row, list) and len(row) > 0 and all(isinstance(c, dict) for c in row) for row in grid)
        and all(len(row) == len(grid[0]) for row in grid)
    )
