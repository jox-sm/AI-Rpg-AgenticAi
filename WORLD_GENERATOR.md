# World Generator Node (`node0_worldgen`) — Spec

Status: SPEC (not yet implemented). Author: agent recon 2026-10-03. Reviewer: owner.

## 1. Goal

A pure-deterministic, zero-LLM graph node that owns the living world:

- first-turn population (start cell, nearby monsters, player position)
- full lifecycle every turn (movement, fog-of-war, mining, traps, respawns)
- honors the `.md` block spec (`plan.md` §§ Block Schema / World System):
  blocks are `(x, y, depth)` with `weight`, `durability {current/max/mining_threshold}`,
  `trap`, `items`, `physics {temperature/wetness/...}` — so players can actually mine.

Non-goals: LLM flavor text (stays $0), full 3D lattice persistence (lazy per-cell only),
combat resolution (stays in node4), narrative (stays in node6).

## 2. What exists today (verified 2026-10-03)

| Piece | Location | State |
|---|---|---|
| Seeded 6×6 world (biomes, weather, buildings, NPCs, per-cell enemies name+level, factions, events) | `rpg_ai_server/scripts/world_generator.py:generate_world` | Built, half-consumed |
| Grid → combat entities (`monster`/`npc` in `GridCell.entities`) | `world_generator.py:_cell_to_gridcell` | Built, never read by graph |
| `world_to_meta` (name/seed/regions/events/factions) | `world_generator.py:223` | Drops grid detail |
| Initial world build per request | `engine/orchestrator.py:_build_initial_state:55` | Outside graph, one-shot |
| On-demand ambush spawn (name-table HP/AC) | `agents/node4_parallel.py:_ensure_target` | Stopgap — no grid consult |
| Player position / depth / block durability / mining | — | **Do not exist** (`explored: False` never flips; `durability` only on `InventoryItem`, `schemas/types.py:110`) |
| Move/mine intent | `agents/classifier.py` intents | **Missing** (movement hides in `explore`) |

## 3. Placement

```
START → classifier → worldgen → react_router ⇄ {search|image|redescribe}
  → mechanics (node4) → context_refresh → summarizer → story → pusher → END
```

Gate inside the node (no router change): first turn does full population,
later turns do the light lifecycle pass. Node is pure (dict in → dict out),
no Redis, no HTTP, no LLM — trivially testable, unmockable-proof
(tests monkeypatch `get_openrouter_direct` to boom).

## 4. State contract (all under `game_data`, persisted via existing `save_state`)

```python
game_data["populated"]: bool          # False → full population pass
game_data["player_pos"]: {"x": int, "y": int, "depth": int}
game_data["turn"]: int                # world clock, +1 per worldgen run
game_data["monsters"]: [              # canon fighting sheets (node4 reads/writes)
  {"name": str, "hp": int, "max_hp": int, "ac": int,
   "status": "hostile|neutral|dead", "cell": [x, y], "respawn_at": int}
]
game_data["blocks"]: {                # lazy per-cell block detail, LRU-capped (~12)
  "x:y:depth": {"blocks": [Block...], "explored": bool}
}
```

`Block` (subset of `plan.md` schema, JSON-safe):

```python
{"x": int, "y": int, "depth": int, "block_id": str, "biome": str,
 "weight": float,
 "durability": {"current": int, "max": int, "mining_threshold": int},
 "trap": {"is_trap": bool, "trigger_effect": str, "damage_on_trigger": int, ...} | None,
 "items": [{"item_id": str, "qty": int}],
 "physics": {"temperature": float, "wetness": float}}
```

Seed for cell blocks: `f"{sid}:{x}:{y}:{depth}"` (stable across turns).

## 5. Behaviors

### 5.1 First turn (no `populated` flag)

1. Start cell: seeded pick, plains-preferring (`plains|forest|meadow` substring else fallback),
   avoids volcano/deepslate cells.
2. `player_pos = {x, y, depth: 0}`, mark cell explored.
3. Convert grid enemies of start cell + 8 neighbors into monster sheets:
   `hp = 12 + level*4`, `ac = 10 + level//2`, `max_hp = hp`, `status` hostile
   (passive-biome creatures → neutral). Grid is canon; `_SPAWN_TABLE`
   (node4) becomes fallback-only for off-grid named targets.
4. Emit `nearby_threats: str` (top 3 by cell distance) for story/mechanics context.
5. Set `populated = True`.

### 5.2 Movement (every turn, deterministic verb parse — no classifier change)

Verbs: `go|move|head|walk|run|travel <north|south|east|west|n|s|e|w>`,
`enter|exit`, `up|down|climb|descend` (depth ± 1, clamped to [-3, +2]).
Bounds: 6×6, depth clamp; illegal move → `- world: blocked (edge of known lands)` line, no state change.
On success: update `player_pos`, flip `explored`, spawn that cell's encounters
(same formula as 5.1), append `- world: moved to (x,y,d) — <biome>, <threats|quiet>` to `tool_results`.

### 5.3 Mining / harvest (`mine|dig|chop|harvest|break` + optional target)

1. Resolve target block in current cell (named match else lowest durability).
2. Damage = `1 + strength//4 + tool bonus` (tool bonus from wielded item name match:
   pickaxe +3 stone/ore, axe +3 wood — data table in node, no LLM).
3. `durability.current -= damage`; on `<= mining_threshold`: move `items[]` → return
   as `inventory_drops` for node4 merge, mark block `depleted` (no respawn).
4. Trap check on break when `trap.is_trap`: append damage/status line
   (`damage_on_trigger`, clear trap so it fires once).
5. Append `- world: mined <block> (a→b)[, found <items>][, trap: <effect>]` to `tool_results`.

### 5.4 Respawns & clock

`turn += 1` each run. Dead monsters with `respawn_at <= turn` and player outside
their cell respawn at full HP (`respawn_at = turn + 8` set on kill — node4 sets it;
worldgen honors it). Cleared traps and depleted blocks never restore.

### 5.5 node4 cooperation (small edits, no rewrite)

- `_ensure_target`: `game_data["monsters"]` lookup first (unchanged) → grid sheets
  are found naturally; name-table spawn stays as off-grid fallback.
- `_snapshot` already carries `game_data` (added 2026-10-03).
- Mining `inventory_drops` returned by worldgen merge into inventory via the existing
  inventory-overwrite path (worldgen runs before mechanics; node4 snapshot includes them).
- On kill, node4 sets `respawn_at = game_data["turn"] + 8`.

## 6. Files

| Action | File |
|---|---|
| CREATE node | `rpg_ai_server/agents/node0_worldgen.py` (pure fns + `node0_worldgen(state)`; helpers importable by node4: `spawn_stats_for(name, level)`) |
| EDIT wiring | `rpg_ai_server/engine/graph_v2.py` (add node + edge `classifier → worldgen → react_router`; legacy `graph_builder.py` untouched) |
| EDIT fallback | `rpg_ai_server/agents/node4_parallel.py` (import shared spawn helper, set `respawn_at` on kill) |
| CREATE tests | `tests/test_worldgen.py` (determinism, bounds, mining math, traps, respawns, no-LLM/network guard) |

## 7. Open decisions (defaults proposed; owner overrides)

1. Persisted-cells cap: **12** (LRU drop) — bounds `games:{sid}:state` growth.
2. Grid-level → HP/AC: **`hp = 12 + level*4`, `ac = 10 + level//2`**.
3. Mining loot path: **direct to inventory** via node4 merge (visible next turn).
4. Depth range: **[-3, +2]** (surface 0, caves negative, ridges positive).

## 8. Verification

1. `python -m pytest -q` — full suite incl. new `test_worldgen.py` (target 120+ passed).
2. Local probe (no network): fresh sid → start cell + monsters deterministic across
   two runs; `go north` → pos change + explored flip; `mine stone` ×N → durability
   drop → depletion → loot; trap cell → trigger line; kill → `respawn_at` set →
   advance 8 turns → respawned.
3. Live: restart worker (picks up node), `temp_input.py --sid <fresh> "look around"`,
   then `"go north"`, then `"mine"`, then `"attack the <spawned enemy>"` — expect
   world lines in `tool_results` and grid-canon (not table-fallback) monsters.
