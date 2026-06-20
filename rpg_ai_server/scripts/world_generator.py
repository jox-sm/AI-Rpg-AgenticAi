from __future__ import annotations

import hashlib
import random
from typing import Any, Dict, List, Optional, Tuple

from ..schemas.enums import Terrain
from ..schemas.types import GridCell
from ..utils.items_db import ItemsDB

_ITEMS_DB = ItemsDB()
_GRID_SIZE = 6

_BIOME_TO_TERRAIN = {
    "forest": Terrain.FOREST,
    "plains": Terrain.PLAINS,
    "desert": Terrain.DESERT,
    "mountain": Terrain.MOUNTAINS,
    "swamp": Terrain.SWAMP,
    "tundra": Terrain.TUNDRA,
    "jungle": Terrain.JUNGLE,
    "volcano": Terrain.VOLCANO,
    "cave": Terrain.CAVE,
    "ocean": Terrain.OCEAN,
    "city": Terrain.CITY,
    "lake": Terrain.RIVER,
    "river": Terrain.RIVER,
    "frozen": Terrain.TUNDRA,
    "rocky": Terrain.DESERT,
    "charred": Terrain.VOLCANO,
    "ancient": Terrain.FOREST,
}


def _seeded_rng(seed: str) -> random.Random:
    return random.Random(hashlib.md5(seed.encode()).hexdigest())


def _pick(candidates: List[Dict[str, Any]], rng: random.Random, count: int = 1) -> List[Dict[str, Any]]:
    if not candidates:
        return []
    k = min(count, len(candidates))
    return rng.sample(candidates, k)


def _biome_to_terrain(biome_name: str) -> Terrain:
    lower = biome_name.lower()
    for keyword, terrain in _BIOME_TO_TERRAIN.items():
        if keyword in lower:
            return terrain
    return Terrain.UNKNOWN


def _biome_adjacency(rng: random.Random, x: int, y: int, grid: List[List[Optional[str]]]) -> str:
    neighbors = []
    if x > 0 and grid[y][x - 1]:
        neighbors.append(grid[y][x - 1])
    if y > 0 and grid[y - 1][x]:
        neighbors.append(grid[y - 1][x])
    if not neighbors:
        return ""
    biome_name = rng.choice(neighbors)
    if rng.random() < 0.6:
        return biome_name
    return ""


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

            resources = biome_data.get("Resources", "")
            difficulty_str = biome_data.get("Difficulty Level", "1")
            try:
                difficulty_min, difficulty_max = [int(p.strip()) for p in difficulty_str.split("-")]
            except (ValueError, AttributeError):
                difficulty_min = difficulty_max = int(difficulty_str) if difficulty_str.isdigit() else 1

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


def world_to_grid_data(world: Dict[str, Any]) -> Dict[str, List[GridCell]]:
    cells: List[GridCell] = []
    for y, row in enumerate(world["grid"]):
        for x, cell in enumerate(row):
            cells.append(_cell_to_gridcell(cell, x, y))
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
    if 0 <= y < len(world["grid"]) and 0 <= x < len(world["grid"][y]):
        return world["grid"][y][x]
    return None


def coord_to_key(x: int, y: int) -> str:
    return f"coord:{x}:{y}"
