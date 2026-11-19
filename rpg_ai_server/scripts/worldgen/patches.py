"""Sparse player-edit overlay: partial cell edits persist in game_data."""
from __future__ import annotations

import copy
from typing import Any, Dict

from .common import coord_to_key

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
    from .world import get_world_cell  # local: avoids patches<->world cycle
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
