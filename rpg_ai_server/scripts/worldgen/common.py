"""Shared world constants, biome mapping, deterministic RNG + item-db lists."""
from __future__ import annotations

import hashlib
import random
from typing import Any, Dict, List, Optional, Tuple

from ...schemas.enums import Terrain
from ...utils.items_db import ItemsDB

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

def coord_to_key(x: int, y: int) -> str:
    return f"coord:{x}:{y}"

import re as _re

WORLD_INITIAL_SIZE = 6
WORLD_EXPAND_MARGIN = 1
WORLD_EXPAND_BY = 2
WORLD_MAX_SIZE = 64
WORLD_REGION_SIZE = 8

_FALLBACK_BIOME_NAMES = ["Plains", "Forest", "Desert", "Swamp", "Tundra", "Volcano"]

_MOVE_RE = _re.compile(
    r"\b(?:go|move|head|walk|run|travel|step|march|journey|sail|ride|fly|venture|proceed|advance)\s+"
    r"(north|south|east|west|n|s|e|w)\b",
    _re.IGNORECASE,
)
_BARE_DIR_RE = _re.compile(r"^\s*(north|south|east|west)\s*[.!?]?\s*$", _re.IGNORECASE)

_DIR_DELTA = {
    "north": (0, -1), "n": (0, -1),
    "south": (0, 1), "s": (0, 1),
    "east": (1, 0), "e": (1, 0),
    "west": (-1, 0), "w": (-1, 0),
}

def _db_lists() -> Dict[str, List[Dict[str, Any]]]:
    """Snapshot the item-db lists once per call (cheap, in-memory)."""
    try:
        return {
            "biomes": _ITEMS_DB.filter(_file="biomes") or [],
            "weather": _ITEMS_DB.filter(_file="weather") or [],
            "buildings": _ITEMS_DB.filter(_file="buildings") or [],
            "npcs": _ITEMS_DB.filter(_file="npcs") or [],
            "events": _ITEMS_DB.filter(_file="events") or [],
            "enemies": _ITEMS_DB.filter(_file="enemies") or [],
            "factions": _ITEMS_DB.filter(_file="factions") or [],
        }
    except Exception:
        return {"biomes": [], "weather": [], "buildings": [], "npcs": [], "events": [], "enemies": [], "factions": []}


def _region_biome_name(world_seed: str, wx: int, wy: int, biome_names: List[str]) -> str:
    """Deterministic region-lattice biome: 8x8 blocks share one biome (order-independent)."""
    names = biome_names or _FALLBACK_BIOME_NAMES
    rx = wx // WORLD_REGION_SIZE
    ry = wy // WORLD_REGION_SIZE
    rng = _seeded_rng(f"{world_seed}:region:{rx}:{ry}")
    return rng.choice(names)
