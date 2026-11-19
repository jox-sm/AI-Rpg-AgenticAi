"""Parse cardinal movement verbs and move the player through the world."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .common import _BARE_DIR_RE, _DIR_DELTA, _MOVE_RE
from .patches import coord_to_key, get_patches
from .world import ensure_world, get_world_cell, maybe_expand_world

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
