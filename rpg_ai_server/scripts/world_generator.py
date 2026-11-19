"""Compatibility facade — world generator moved into scripts/worldgen/.

All public names are re-exported unchanged; existing imports and callers stay valid.
"""
from .worldgen.cells import _valid_grid, generate_cell
from .worldgen.common import (
    WORLD_EXPAND_BY, WORLD_EXPAND_MARGIN, WORLD_INITIAL_SIZE, WORLD_MAX_SIZE,
    WORLD_REGION_SIZE, _BIOME_TO_TERRAIN, _db_lists, _region_biome_name,
    _seeded_rng, coord_to_key,
)
from .worldgen.finite import (
    _cell_to_gridcell, _origin, generate_world, get_cell_meta,
    grid_to_grid_data, world_to_grid_data, world_to_meta,
)
from .worldgen.movement import move_player, parse_move
from .worldgen.patches import OVERLAY_KEY, _deep_merge, clear_patch, get_patches, patch_cell
from .worldgen.world import _local_pos, ensure_world, get_world_cell, maybe_expand_world

__all__ = [
    "generate_world", "generate_cell", "ensure_world", "get_world_cell",
    "maybe_expand_world", "move_player", "parse_move", "patch_cell", "clear_patch",
    "get_patches", "coord_to_key", "world_to_grid_data", "grid_to_grid_data",
    "world_to_meta", "get_cell_meta", "OVERLAY_KEY", "WORLD_INITIAL_SIZE",
    "WORLD_EXPAND_MARGIN", "WORLD_EXPAND_BY", "WORLD_MAX_SIZE", "WORLD_REGION_SIZE",
    "_cell_to_gridcell", "_origin", "_valid_grid", "_deep_merge", "_local_pos",
    "_db_lists", "_region_biome_name", "_seeded_rng", "_BIOME_TO_TERRAIN",
]
