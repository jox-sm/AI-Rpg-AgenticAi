from __future__ import annotations

import copy
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

            from ..scripts.xp_loot import parse_level_range
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
    from ..utils.coerce import to_int
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


def coord_to_key(x: int, y: int) -> str:
    return f"coord:{x}:{y}"


# ── Cell patches overlay (sparse player edits) ──
#
# Base terrain is never stored: any coordinate regenerates deterministically
# from ``world_seed``. Player edits (digging, building, ...) live as sparse
# JSON snapshots in ``game_data["cell_patches"]`` keyed by ``coord_to_key``.
# The overlay always wins: patched cells return as-is, everything else falls
# through to the stored grid / pure regeneration. Untouched coords cost zero
# storage, and patches ride inside ``game_data`` so they persist + sync
# through the normal state/Redis path with no extra plumbing.

OVERLAY_KEY = "cell_patches"


def get_patches(game_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return the overlay mapping (empty if none). Never creates it."""
    patches = (game_data or {}).get(OVERLAY_KEY)
    return patches if isinstance(patches, dict) else {}


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """Merge ``patch`` onto ``base``: nested dicts recurse, everything else replaces."""
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value) if isinstance(value, (dict, list)) else value
    return merged


def patch_cell(game_data: Dict[str, Any], wx: int, wy: int, patch: Dict[str, Any]) -> Dict[str, Any]:
    """Record a player edit at world coords as a full-cell snapshot.

    The patch is deep-merged onto the cell's current effective content
    (previous patch, stored grid cell, or fresh regeneration) so partial
    edits preserve everything else. The snapshot wins on every future read.
    Out-of-window coords are patched without growing the stored grid.
    """
    if not isinstance(game_data, dict):
        raise TypeError("game_data must be a dict")
    if not isinstance(patch, dict):
        raise TypeError("patch must be a dict")
    wx, wy = int(wx), int(wy)
    current = get_world_cell(game_data, wx, wy, _store=False) or {}
    snapshot = _deep_merge(dict(current), patch)
    snapshot["x"], snapshot["y"] = wx, wy
    patches = game_data.get(OVERLAY_KEY)
    if not isinstance(patches, dict):
        patches = {}
        game_data[OVERLAY_KEY] = patches
    patches[coord_to_key(wx, wy)] = snapshot
    return snapshot


def clear_patch(game_data: Dict[str, Any], wx: int, wy: int) -> bool:
    """Drop the overlay snapshot at world coords; base regeneration shows through again."""
    patches = get_patches(game_data)
    key = coord_to_key(int(wx), int(wy))
    if key in patches:
        del patches[key]
        return True
    return False


# ── Infinite deterministic world (seeded per-coordinate generation) ──
#
# The world persists in ``game_data`` as a dense 2D array plus metadata:
#
#   game_data["world_seed"]: str   # stable per game (defaults to the sid)
#   game_data["world"]:      dict  # meta (name/seed/regions/...)
#   game_data["grid"]:       List[List[dict]]  # row-major [ly][lx], full cell objects
#   game_data["origin"]:     {"x": int, "y": int}  # world coords of grid[0][0]
#   game_data["player_pos"]: {"x": int, "y": int, "depth": int}  # world coords
#
# Player edits ride separately in ``game_data["cell_patches"]``: sparse
# ``"coord:x:y"`` -> full-cell snapshots that override generation on read.
#
# Every world coordinate maps to exactly one deterministic cell for a given
# difficulty scalar: ``generate_cell(seed, x, y, scalar)`` regenerates the
# identical place on revisit. Stored (materialized) cells are immutable
# afterwards, so only freshly generated frontier reflects a risen scalar.
# ``maybe_expand_world`` materializes new rows/columns when the player nears a
# border; ``get_world_cell`` falls back to pure regeneration for out-of-bounds
# lookahead without storing anything.

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

    from ..scripts.xp_loot import parse_level_range
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


def ensure_world(game_data: Dict[str, Any], world_seed: Optional[str] = None) -> Dict[str, Any]:
    """Ensure ``game_data`` carries a valid world grid + origin + player_pos.

    Migrates legacy saves (6x6 grid, no origin/player) in place; generates a fresh
    ``WORLD_INITIAL_SIZE`` deterministic grid otherwise. Idempotent.
    """
    if not isinstance(game_data, dict):
        raise TypeError("game_data must be a dict")
    seed = str(world_seed or game_data.get("world_seed") or (game_data.get("world") or {}).get("seed") or "world")
    game_data["world_seed"] = seed

    grid = game_data.get("grid")
    if not _valid_grid(grid):
        from ..scripts.xp_loot import difficulty_scalar as _wscalar
        lists = _db_lists()
        size = WORLD_INITIAL_SIZE
        scalar = _wscalar(game_data)
        fresh = [[generate_cell(seed, x, y, lists, scalar) for x in range(size)] for y in range(size)]
        game_data["grid"] = fresh
        game_data["origin"] = {"x": 0, "y": 0}
        cx, cy = size // 2, size // 2
        game_data["player_pos"] = {"x": cx, "y": cy, "depth": 0}
        fresh[cy][cx]["explored"] = True
        biomes_here = sorted({c.get("biome", "Unknown") for row in fresh for c in row})
        game_data.setdefault("world", {})
        if not isinstance(game_data["world"], dict):
            game_data["world"] = {}
        game_data["world"].setdefault("name", "The Unknown Realm")
        game_data["world"]["seed"] = seed
        game_data["world"].setdefault("regions", biomes_here)
        return game_data

    # Migrate legacy grid (no origin / player / seed).
    origin = game_data.get("origin")
    if not isinstance(origin, dict) or "x" not in origin or "y" not in origin:
        game_data["origin"] = {"x": 0, "y": 0}
    pos = game_data.get("player_pos")
    if not isinstance(pos, dict) or "x" not in pos or "y" not in pos:
        h, w = len(grid), len(grid[0])
        cx = int(game_data["origin"]["x"]) + w // 2
        cy = int(game_data["origin"]["y"]) + h // 2
        game_data["player_pos"] = {"x": cx, "y": cy, "depth": int(pos.get("depth", 0)) if isinstance(pos, dict) else 0}
    else:
        game_data["player_pos"] = {"x": int(pos["x"]), "y": int(pos["y"]), "depth": int(pos.get("depth", 0))}
    # Stamp world coords onto legacy cells that lack them (harmless for new cells).
    ox, oy = int(game_data["origin"]["x"]), int(game_data["origin"]["y"])
    for ly, row in enumerate(grid):
        for lx, cell in enumerate(row):
            cell.setdefault("x", ox + lx)
            cell.setdefault("y", oy + ly)
    # Mark the starting cell explored so the map is never fully dark.
    here = get_world_cell(game_data, game_data["player_pos"]["x"], game_data["player_pos"]["y"], _store=True)
    if isinstance(here, dict):
        here["explored"] = True
    return game_data


def _local_pos(game_data: Dict[str, Any]) -> Tuple[int, int, int, int, int, int]:
    """Return (lx, ly, w, h, px, py): player local coords + grid size + world pos."""
    origin = game_data.get("origin") or {"x": 0, "y": 0}
    pos = game_data.get("player_pos") or {"x": 0, "y": 0}
    grid = game_data.get("grid") or []
    h = len(grid)
    w = len(grid[0]) if h else 0
    return int(pos["x"]) - int(origin["x"]), int(pos["y"]) - int(origin["y"]), w, h, int(pos["x"]), int(pos["y"])


def get_world_cell(game_data: Dict[str, Any], wx: int, wy: int, _store: bool = False) -> Optional[Dict[str, Any]]:
    """Return the cell at world coords: stored one if materialized, else pure regeneration.

    With ``_store=False`` (default) out-of-bounds lookups regenerate deterministically
    without growing state — revisits later expand to the identical object.

    Player edits always win: if the overlay holds a snapshot for these coords
    it is returned as-is, ahead of the stored grid and regeneration.
    """
    patched = get_patches(game_data).get(coord_to_key(int(wx), int(wy)))
    if isinstance(patched, dict):
        return patched
    from ..scripts.xp_loot import difficulty_scalar as _wscalar
    grid = game_data.get("grid") or []
    origin = game_data.get("origin") or {"x": 0, "y": 0}
    lx, ly = int(wx) - int(origin["x"]), int(wy) - int(origin["y"])
    if grid and 0 <= ly < len(grid) and 0 <= lx < len(grid[ly]):
        return grid[ly][lx]
    cell = generate_cell(str(game_data.get("world_seed") or "world"), int(wx), int(wy),
                         scalar=_wscalar(game_data))
    if _store:
        # Caller asked for a materialized cell but it is outside the window:
        # grow the window to include it, then return the stored reference.
        maybe_expand_world(game_data)
        grid = game_data.get("grid") or []
        origin = game_data.get("origin") or {"x": 0, "y": 0}
        lx, ly = int(wx) - int(origin["x"]), int(wy) - int(origin["y"])
        if 0 <= ly < len(grid) and 0 <= lx < len(grid[ly]):
            return grid[ly][lx]
    return cell


def maybe_expand_world(
    game_data: Dict[str, Any],
    margin: int = WORLD_EXPAND_MARGIN,
    expand_by: int = WORLD_EXPAND_BY,
    max_size: int = WORLD_MAX_SIZE,
) -> Dict[str, Any]:
    """Grow the 2D grid when the player is within ``margin`` of any border.

    New rows/columns are generated deterministically per coordinate, so already-
    visited places keep their stored (possibly mutated) cells while never-visited
    frontier regenerates identically on revisit. Returns a report dict.
    """
    ensure_world(game_data, game_data.get("world_seed"))
    from ..scripts.xp_loot import difficulty_scalar as _wscalar
    report: Dict[str, Any] = {"expanded": False, "directions": [], "new_size": None, "blocked": False}
    seed = str(game_data.get("world_seed") or "world")
    lists = _db_lists()
    scalar = _wscalar(game_data)
    # Loop: a single pass may not suffice after a long jump; cap iterations.
    for _ in range(8):
        lx, ly, w, h, px, py = _local_pos(game_data)
        ox, oy = int(game_data["origin"]["x"]), int(game_data["origin"]["y"])
        need_left = lx < margin
        need_right = lx >= w - margin
        need_top = ly < margin
        need_bottom = ly >= h - margin
        if not (need_left or need_right or need_top or need_bottom):
            break
        # Clamp growth to the state-explosion cap.
        grow_w = (expand_by if need_left else 0) + (expand_by if need_right else 0)
        grow_h = (expand_by if need_top else 0) + (expand_by if need_bottom else 0)
        if w + grow_w > max_size:
            over = w + grow_w - max_size
            if need_left and need_right:
                cut = min(over // 2 + over % 2, expand_by)
                grow_w -= cut * 2 - (1 if over % 2 and cut else 0)
            elif need_left or need_right:
                grow_w -= min(over, expand_by)
            if w + grow_w > max_size:
                report["blocked"] = True
                need_left = need_right = False
        if h + grow_h > max_size:
            over = h + grow_h - max_size
            if need_top and need_bottom:
                grow_h -= min(over, expand_by * 2 - (0 if over <= expand_by else 0))
            elif need_top or need_bottom:
                grow_h -= min(over, expand_by)
            if h + grow_h > max_size:
                report["blocked"] = True
                need_top = need_bottom = False
        if not (need_left or need_right or need_top or need_bottom):
            break

        grid = game_data["grid"]
        left = expand_by if need_left else 0
        right = expand_by if need_right else 0
        top = expand_by if need_top else 0
        bottom = expand_by if need_bottom else 0
        # Re-clamp each side individually against the cap.
        while w + left + right > max_size and (left or right):
            if left >= right and left:
                left -= 1
            elif right:
                right -= 1
            else:
                break
        while h + top + bottom > max_size and (top or bottom):
            if top >= bottom and top:
                top -= 1
            elif bottom:
                bottom -= 1
            else:
                break
        if not (left or right or top or bottom):
            report["blocked"] = True
            break

        new_ox, new_oy = ox - left, oy - top
        new_w, new_h = w + left + right, h + top + bottom
        new_grid: List[List[Dict[str, Any]]] = [[None] * new_w for _ in range(new_h)]  # type: ignore[list-item]
        for ny in range(new_h):
            for nx in range(new_w):
                old_lx, old_ly = nx - left, ny - top
                if 0 <= old_lx < w and 0 <= old_ly < h:
                    new_grid[ny][nx] = grid[old_ly][old_lx]
                else:
                    new_grid[ny][nx] = generate_cell(seed, new_ox + nx, new_oy + ny, lists, scalar)
        game_data["grid"] = new_grid
        game_data["origin"] = {"x": new_ox, "y": new_oy}
        if need_left:
            report["directions"].append("west")
        if need_right:
            report["directions"].append("east")
        if need_top:
            report["directions"].append("north")
        if need_bottom:
            report["directions"].append("south")
        report["expanded"] = True
    lx, ly, w, h, _, _ = _local_pos(game_data)
    report["new_size"] = [w, h]
    report["player_local"] = [lx, ly]
    if isinstance(game_data.get("world"), dict):
        game_data["world"]["grid_size"] = max(w, h)
    return report


def parse_move(prompt: Any) -> Optional[Tuple[int, int]]:
    """Parse a cardinal move verb from free text → (dx, dy). None if no move."""
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    m = _MOVE_RE.search(prompt) or _BARE_DIR_RE.match(prompt)
    if not m:
        return None
    return _DIR_DELTA[m.group(1).lower()]


def move_player(game_data: Dict[str, Any], dx: int, dy: int, world_seed: Optional[str] = None) -> Dict[str, Any]:
    """Move the player by (dx, dy) world cells, marking explored + expanding as needed."""
    ensure_world(game_data, world_seed or game_data.get("world_seed"))
    pos = game_data["player_pos"]
    pos["x"], pos["y"] = int(pos["x"]) + int(dx), int(pos["y"]) + int(dy)
    info: Dict[str, Any] = {"moved_to": [pos["x"], pos["y"]]}
    cell = get_world_cell(game_data, pos["x"], pos["y"], _store=False)
    if isinstance(cell, dict):
        info["biome"] = cell.get("biome", "Unknown")
    # Materialize + mark explored if inside the window after expansion.
    report = maybe_expand_world(game_data)
    info["expansion"] = report
    inside = get_world_cell(game_data, pos["x"], pos["y"], _store=False)
    # get_world_cell returns the stored ref when in bounds → flag it explored.
    grid = game_data.get("grid") or []
    origin = game_data.get("origin") or {"x": 0, "y": 0}
    lx, ly = pos["x"] - int(origin["x"]), pos["y"] - int(origin["y"])
    if 0 <= ly < len(grid) and 0 <= lx < len(grid[ly]):
        grid[ly][lx]["explored"] = True
        inside = grid[ly][lx]
        info["biome"] = inside.get("biome", info.get("biome", "Unknown"))
    # Keep the overlay copy in sync when the visited cell is player-patched
    # (e.g. standing on edited ground at the capped border, outside the grid).
    overlay_hit = get_patches(game_data).get(coord_to_key(pos["x"], pos["y"]))
    if isinstance(overlay_hit, dict):
        overlay_hit["explored"] = True
    return info
