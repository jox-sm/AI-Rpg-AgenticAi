"""Finite 6x6 world generation + GridCell projections (legacy map view)."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from ...schemas.types import GridCell
from .common import (
    _GRID_SIZE, _ITEMS_DB, _biome_adjacency, _biome_to_terrain, _pick,
    _seeded_rng,
)

def generate_world(
    seed: Optional[str] = None,
    map_name: str = "",
    region_count: int = 4,
) -> Dict[str, Any]:
    rng = _seeded_rng(seed or str(random.random()))

    biomes = _ITEMS_DB.filter(_file="biomes")
    all_weather = _ITEMS_DB.filter(_file="weather")
    all_buildings = _ITEMS_DB.filter(_file="buildings")
    all_npcs = _ITEMS_DB.filter(_file="npcs")
    all_events = _ITEMS_DB.filter(_file="events")
    all_enemies = _ITEMS_DB.filter(_file="enemies")
    all_factions = _ITEMS_DB.filter(_file="factions")

    if not biomes:
        raise RuntimeError("No biomes found in items-db")

    regions = rng.sample(biomes, min(region_count, len(biomes)))
    region_fallback = biomes[0]
    grid_simple: List[List[Optional[str]]] = [[None] * _GRID_SIZE for _ in range(_GRID_SIZE)]
    region_centers: List[Tuple[int, int, Dict[str, Any]]] = []

    for region in regions:
        cx = rng.randint(0, _GRID_SIZE - 1)
        cy = rng.randint(0, _GRID_SIZE - 1)
        region_name = region.get("name", "Unknown")
        region_centers.append((cx, cy, region))
        grid_simple[cy][cx] = region_name

    for y in range(_GRID_SIZE):
        for x in range(_GRID_SIZE):
            if grid_simple[y][x] is not None:
                continue
            neighbor_biome = _biome_adjacency(rng, x, y, grid_simple)
            if neighbor_biome:
                grid_simple[y][x] = neighbor_biome
            else:
                distances = [(abs(x - cx) + abs(y - cy), region) for cx, cy, region in region_centers]
                distances.sort(key=lambda t: t[0])
                grid_simple[y][x] = distances[0][1].get("name", "Unknown")

    grid_meta: List[List[Dict[str, Any]]] = []
    for y in range(_GRID_SIZE):
        row = []
        for x in range(_GRID_SIZE):
            biome_name = grid_simple[y][x]
            biome_data = next((b for b in biomes if b.get("name") == biome_name), region_fallback)

            cell_weather = _pick(all_weather, rng, rng.randint(1, 2))
            cell_buildings = _pick(all_buildings, rng, rng.randint(0, 2))
            cell_npcs = _pick(all_npcs, rng, max(1, rng.randint(0, 3)))
            cell_events = _pick(all_events, rng, rng.randint(0, 1))

            enemy_names = biome_data.get("Enemies", "")
            cell_enemies = []
            if enemy_names:
                for e_name in [s.strip() for s in enemy_names.split(",")]:
                    found = _ITEMS_DB.get_by_name(e_name)
                    if found:
                        cell_enemies.append(found)
            if not cell_enemies:
                cell_enemies = _pick(all_enemies, rng, rng.randint(1, 2))

            from ...scripts.xp_loot import parse_level_range
            resources = biome_data.get("Resources", "")
            difficulty_min, difficulty_max = parse_level_range(biome_data.get("Difficulty Level", "1"))

            cell = {
                "biome": biome_name,
                "terrain": biome_data.get("Terrain Type", "Open field"),
                "temperature": biome_data.get("Temperature Range", ""),
                "humidity": biome_data.get("Humidity", ""),
                "weather": [w.get("name", "Clear") for w in cell_weather],
                "resources": [r.strip() for r in resources.split(",") if r.strip()],
                "difficulty": {"min": difficulty_min, "max": difficulty_max},
                "buildings": [
                    {"name": b.get("name", ""), "type": b.get("Type", ""), "size": b.get("Size", "")}
                    for b in cell_buildings
                ],
                "npcs": [
                    {"name": n.get("name", ""), "role": n.get("Role", ""), "personality": n.get("Personality", "")}
                    for n in cell_npcs
                ],
                "enemies": [
                    {"name": e.get("name", ""), "level": e.get("Level", difficulty_min)}
                    for e in cell_enemies
                ],
                "events": [e.get("name", "") for e in cell_events],
                "factions": [f.get("name", "") for f in _pick(all_factions, rng, rng.randint(0, 2))],
                "explored": False,
                "features": [],
            }
            row.append(cell)
        grid_meta.append(row)

    major_events = _pick(all_events, rng, rng.randint(2, 4))
    world_name_entry = _ITEMS_DB.get_by_name("The Realm of Eldoria") if not map_name else None
    world_name = map_name or (world_name_entry.get("name", "The Unknown Realm") if isinstance(world_name_entry, dict) else "The Unknown Realm")

    return {
        "name": world_name,
        "seed": seed or "",
        "grid_size": _GRID_SIZE,
        "grid": grid_meta,
        "regions": [r.get("name", "Unknown") for r in regions],
        "current_events": [e.get("name", "") for e in major_events],
        "factions_present": list(set(
            f.get("name", "") for region in regions
            for f in _pick(all_factions, rng, rng.randint(1, 3))
        )),
    }

def _cell_to_gridcell(cell: Dict[str, Any], x: int, y: int) -> GridCell:
    biome_name = cell.get("biome", "Unknown")
    terrain = _biome_to_terrain(biome_name)

    entities: List[Dict[str, Any]] = []
    for e in cell.get("enemies", []):
        entities.append({"type": "monster", "name": e.get("name", ""), "level": e.get("level", 1)})
    for n in cell.get("npcs", []):
        entities.append({"type": "npc", "name": n.get("name", ""), "role": n.get("role", "")})

    desc_parts = [f"A {biome_name.lower()} area."]
    weather = cell.get("weather", [])
    if weather:
        desc_parts.append(f"Weather: {', '.join(weather[:2])}.")
    buildings = cell.get("buildings", [])
    if buildings:
        desc_parts.append(f"Contains: {', '.join(b.get('name', '') for b in buildings[:2])}.")
    features = cell.get("features", [])
    if features:
        desc_parts.append(f"Features: {', '.join(features[:2])}.")

    return GridCell(
        cell=(x, y),
        terrain=terrain,
        entities=entities,
        description=" ".join(desc_parts),
        prerequisites=[],
    )


def _origin(origin: Any) -> Tuple[int, int]:
    """World coords of grid[0][0]; garbage in, (0, 0) out."""
    from ...utils.coerce import to_int
    if not isinstance(origin, dict):
        return 0, 0
    return to_int(origin.get("x", 0)), to_int(origin.get("y", 0))


def world_to_grid_data(world: Dict[str, Any]) -> Dict[str, List[GridCell]]:
    cells: List[GridCell] = []
    ox, oy = _origin(world.get("origin"))
    for y, row in enumerate(world["grid"]):
        for x, cell in enumerate(row):
            cells.append(_cell_to_gridcell(cell, ox + x, oy + y))
    return {"all": cells}


def grid_to_grid_data(grid: List[List[Dict[str, Any]]], origin: Optional[Dict[str, int]] = None) -> Dict[str, List[GridCell]]:
    """Flat GridCell view of a 2D grid, using world coords (origin offset)."""
    ox, oy = _origin(origin)
    cells: List[GridCell] = []
    for y, row in enumerate(grid or []):
        for x, cell in enumerate(row or []):
            if isinstance(cell, dict):
                cells.append(_cell_to_gridcell(cell, ox + x, oy + y))
    return {"all": cells}


def world_to_meta(world: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": world["name"],
        "seed": world["seed"],
        "grid_size": world["grid_size"],
        "regions": world["regions"],
        "current_events": world["current_events"],
        "factions_present": world["factions_present"],
    }


def get_cell_meta(world: Dict[str, Any], x: int, y: int) -> Optional[Dict[str, Any]]:
    """Get a cell by *world* coords (honors ``origin``); legacy local-index callers pass 0-based coords with origin (0,0)."""
    grid = world.get("grid") or []
    if not grid:
        return None
    ox, oy = _origin(world.get("origin"))
    lx, ly = x - ox, y - oy
    if 0 <= ly < len(grid) and 0 <= lx < len(grid[ly]):
        return grid[ly][lx]
    return None

