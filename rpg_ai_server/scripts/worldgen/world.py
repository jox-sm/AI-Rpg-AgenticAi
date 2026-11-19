"""World lifecycle: ensure/migrate, cell reads, border expansion."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .cells import _valid_grid, generate_cell
from .common import (
    WORLD_EXPAND_BY, WORLD_EXPAND_MARGIN, WORLD_INITIAL_SIZE, WORLD_MAX_SIZE,
    _db_lists,
)
from .patches import coord_to_key, get_patches

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
        from ...scripts.xp_loot import difficulty_scalar as _wscalar
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
    from ...scripts.xp_loot import difficulty_scalar as _wscalar
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
    from ...scripts.xp_loot import difficulty_scalar as _wscalar
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
