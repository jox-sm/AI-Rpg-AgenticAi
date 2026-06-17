# Game Mechanics — Algorithms & Systems

---

## Dijkstra's Algorithm (Pathfinding)

Used for shortest-path distance calculations across the weighted world graph.

### How It Works
1. Each block has a **weight** representing traversal cost.
2. Dijkstra explores neighbors by lowest cumulative cost.
3. Returns shortest path between any two points.

### Weight Table

| Block Type | Base Weight | Formula | Example Cost |
|------------|-------------|---------|--------------|
| Grass | 1.0 | base | 1.0 |
| Stone | 1.2 | base | 1.2 |
| Gravel | 1.5 | base | 1.5 |
| Sand | 1.8 | base | 1.8 |
| Water | 100 / monster_water_resistance | inverse | 100 / 50 = 2.0 |
| Lava | 200 / monster_fire_resistance | inverse | 200 / 90 = 2.22 |
| Ice | 0.8 | base (slippery) | 0.8 |
| Mud | 2.5 | base (slow) | 2.5 |
| Quicksand | 5.0 | base (trap) | 5.0 |

### Implementation

```python
import heapq

def dijkstra(graph, start, end):
    """
    graph: dict of {node: [(neighbor, weight), ...]}
    start: starting node
    end: target node
    Returns: (shortest_cost, path_list)
    """
    queue = [(0, start, [])]
    visited = set()
    
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        
        if node in visited:
            continue
        visited.add(node)
        
        path = path + [node]
        
        if node == end:
            return (cost, path)
        
        for (neighbor, weight) in graph.get(node, []):
            if neighbor not in visited:
                heapq.heappush(queue, (cost + weight, neighbor, path))
    
    return (float('inf'), [])  # No path found

# Example usage:
# graph = {
#     (0,0): [((0,1), 1.0), ((1,0), 1.0)],
#     (0,1): [((0,0), 1.0), ((0,2), 1.2), ((1,1), 1.5)],
#     ...
# }
# cost, path = dijkstra(graph, (0,0), (5,5))
```

### Path Cost Calculation Example
```
Path from (0,0) to (3,0):
  (0,0) → grass   = 1.0
  (1,0) → stone   = 1.2
  (2,0) → gravel  = 1.5
  (3,0) → grass   = 1.0
  Total cost = 4.7
```

---

## A* Algorithm (Heuristic Pathfinding)

Enhanced Dijkstra with heuristic guidance for faster pathfinding.

### Heuristic Function
```python
def manhattan_distance(a, b):
    """Manhattan distance for grid-based movement."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def euclidean_distance(a, b):
    """Euclidean distance for diagonal movement."""
    return ((a[0] - b[0])**2 + (a[1] - b[1])**2) ** 0.5

def chebyshev_distance(a, b):
    """Chebyshev distance for 8-directional movement."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
```

### Implementation
```python
import heapq

def a_star(graph, start, end, heuristic):
    """
    A* pathfinding with heuristic.
    Returns: (cost, path)
    """
    queue = [(0 + heuristic(start, end), 0, start, [])]
    visited = set()
    
    while queue:
        (f_score, g_score, node, path) = heapq.heappop(queue)
        
        if node in visited:
            continue
        visited.add(node)
        
        path = path + [node]
        
        if node == end:
            return (g_score, path)
        
        for (neighbor, weight) in graph.get(node, []):
            if neighbor not in visited:
                new_g = g_score + weight
                f = new_g + heuristic(neighbor, end)
                heapq.heappush(queue, (f, new_g, neighbor, path))
    
    return (float('inf'), [])

# Usage:
# cost, path = a_star(graph, (0,0), (5,5), manhattan_distance)
```

### When to Use A* vs Dijkstra
| Scenario | Algorithm | Reason |
|----------|-----------|--------|
| Shortest path to known target | A* | Heuristic guides search |
| Explore all reachable nodes | Dijkstra | No target, need full graph |
| Multiple targets | Dijkstra | Run once, query multiple |
| Dynamic obstacles | A* | Re-plan quickly |

---

## BFS (Breadth-First Search — Entity Detection)

Used for entity detection within render distance and visibility checks.

### Implementation
```python
from collections import deque

def bfs_entities(graph, start, max_depth):
    """
    Find all entities within max_depth chunks.
    graph: adjacency list of chunks
    start: player chunk position
    max_depth: render distance in chunks
    Returns: list of (entity, distance)
    """
    queue = deque([(start, 0)])
    visited = {start}
    found_entities = []
    
    while queue:
        node, depth = queue.popleft()
        
        if depth > max_depth:
            continue
        
        # Check for entities in this chunk
        entities = get_entities_at_chunk(node)
        for entity in entities:
            found_entities.append((entity, depth))
        
        # Explore neighbors
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, depth + 1))
    
    return found_entities

# Usage:
# entities = bfs_entities(chunk_graph, player_chunk, render_distance=4)
```

### Diamond Render Pattern
```python
def get_visible_chunks(player_chunk, radius=4):
    """
    Returns chunks in diamond pattern around player.
    """
    px, py = player_chunk
    visible = []
    
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            # Diamond check: |dx| + |dy| <= radius
            if abs(dx) + abs(dy) <= radius:
                visible.append((px + dx, py + dy))
    
    return visible

# Example output for radius=2:
#         -
#     -------
#   -----------
#     -------
#         -
```

---

## Flood Fill (Biome Generation)

Used for biome region filling and connected component detection.

### Implementation
```python
def flood_fill(grid, start, target_biome, new_biome):
    """
    Fill connected region with new biome type.
    grid: 2D array of biome types
    start: (x, y) to start filling
    """
    stack = [start]
    visited = set()
    
    while stack:
        x, y = stack.pop()
        
        if (x, y) in visited:
            continue
        if not (0 <= x < len(grid) and 0 <= y < len(grid[0])):
            continue
        if grid[y][x] != target_biome:
            continue
        
        visited.add((x, y))
        grid[y][x] = new_biome
        
        # Add neighbors (4-directional)
        stack.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])
    
    return visited

# Usage:
# flood_fill(world_grid, (10, 10), "empty", "volcano")
```

---

## Perlin Noise (Terrain Generation)

Used for natural-looking terrain, depth gradients, and temperature distribution.

### Implementation
```python
import math
import random

def perlin_2d(x, y, seed=0):
    """Simple 2D Perlin noise implementation."""
    # Hash function
    def hash_coord(x, y, seed):
        n = x * 374761393 + y * 668265263 + seed
        n = (n ^ (n >> 13)) * 1274126177
        return n & 0x7fffffff
    
    # Grid corners
    xi = int(math.floor(x))
    yi = int(math.floor(y))
    
    xf = x - xi
    yf = y - yi
    
    # Smoothstep
    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    
    # Corner values
    n00 = hash_coord(xi, yi, seed) / 0x7fffffff
    n01 = hash_coord(xi, yi + 1, seed) / 0x7fffffff
    n10 = hash_coord(xi + 1, yi, seed) / 0x7fffffff
    n11 = hash_coord(xi + 1, yi + 1, seed) / 0x7fffffff
    
    # Bilinear interpolation
    nx0 = n00 * (1 - u) + n10 * u
    nx1 = n01 * (1 - u) + n11 * u
    
    return nx0 * (1 - v) + nx1 * v

def generate_heightmap(width, height, scale=0.1, seed=42):
    """Generate heightmap using Perlin noise."""
    heightmap = []
    for y in range(height):
        row = []
        for x in range(width):
            value = perlin_2d(x * scale, y * scale, seed)
            row.append(value)
        heightmap.append(row)
    return heightmap

# Usage:
# heightmap = generate_heightmap(100, 100, scale=0.05)
# Depth = heightmap[y][x] * 200  # 0-200 depth range
```

---

## Fuzzy Logic (Transitions)

Ensures smooth transitions between biome properties (depth, temperature, wetness).

### Rules
```python
def fuzzy_transition(current_value, target_value, distance, max_distance):
    """
    Smooth transition using fuzzy membership.
    current_value: property at current block
    target_value: property at target block
    distance: blocks away from transition point
    max_distance: how many blocks the transition spans
    """
    if distance <= 0:
        return current_value
    if distance >= max_distance:
        return target_value
    
    # Fuzzy membership function (sigmoid-like)
    t = distance / max_distance
    t = t * t * (3 - 2 * t)  # Smoothstep
    
    return current_value + (target_value - current_value) * t

def apply_fuzzy_transitions(chunk_data, transition_chunks=3):
    """
    Apply fuzzy transitions across chunk boundaries.
    """
    for y in range(len(chunk_data)):
        for x in range(len(chunk_data[0])):
            block = chunk_data[y][x]
            
            # Check neighbors for transition zones
            for dx in range(-transition_chunks, transition_chunks + 1):
                for dy in range(-transition_chunks, transition_chunks + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < len(chunk_data[0]) and 0 <= ny < len(chunk_data):
                        neighbor = chunk_data[ny][nx]
                        
                        if neighbor['biome'] != block['biome']:
                            dist = abs(dx) + abs(dy)
                            block['temperature'] = fuzzy_transition(
                                block['temperature'],
                                neighbor['temperature'],
                                dist,
                                transition_chunks
                            )
    
    return chunk_data
```

### Transition Rules
| Property | Max Jump Per Block | Notes |
|----------|-------------------|-------|
| Depth | ±5 per block | Exception: cliffs (±20 allowed) |
| Temperature | ±15°C per block | Volcano approach: ±10 |
| Wetness | ±20 per block | Water edge: ±15 |
| Biome | 1 biome per 3 chunks | Borders are gradual |

---

## Finite State Machine (Entity AI)

Controls entity behavior through state transitions.

### State Definitions
```python
from enum import Enum

class EntityState(Enum):
    IDLE = "idle"
    PATROL = "patrol"
    CHASE = "chase"
    ATTACK = "attack"
    FLEE = "flee"
    DEAD = "dead"
    DORMANT = "dormant"

class TransitionRule:
    def __init__(self, from_state, to_state, condition):
        self.from_state = from_state
        self.to_state = to_state
        self.condition = condition
    
    def check(self, entity, world_state):
        return self.condition(entity, world_state)

# Define transitions
transitions = [
    TransitionRule(EntityState.IDLE, EntityState.PATROL, 
        lambda e, w: random.random() < 0.3),
    TransitionRule(EntityState.PATROL, EntityState.CHASE,
        lambda e, w: e.can_see(w.player)),
    TransitionRule(EntityState.CHASE, EntityState.ATTACK,
        lambda e, w: e.distance_to(w.player) <= e.attack_range),
    TransitionRule(EntityState.CHASE, EntityState.FLEE,
        lambda e, w: e.hp / e.max_hp < e.flee_threshold),
    TransitionRule(EntityState.ATTACK, EntityState.CHASE,
        lambda e, w: e.distance_to(w.player) > e.attack_range),
    TransitionRule(EntityState.ATTACK, EntityState.DEAD,
        lambda e, w: e.hp <= 0),
    TransitionRule(EntityState.FLEE, EntityState.IDLE,
        lambda e, w: e.distance_to(w.player) > e.sight_range),
]
```

### FSM Processor
```python
class StateMachine:
    def __init__(self, entity, transitions):
        self.entity = entity
        self.transitions = transitions
        self.current_state = EntityState.IDLE
    
    def update(self, world_state):
        """Check transitions and execute current state."""
        # Check for valid transitions
        for transition in self.transitions:
            if transition.from_state == self.current_state:
                if transition.condition(self.entity, world_state):
                    self.current_state = transition.to_state
                    break
        
        # Execute state behavior
        self.execute_state(world_state)
    
    def execute_state(self, world_state):
        if self.current_state == EntityState.IDLE:
            self.entity.idle_behavior()
        elif self.current_state == EntityState.PATROL:
            self.entity.patrol_behavior()
        elif self.current_state == EntityState.CHASE:
            self.entity.chase_behavior(world_state.player)
        elif self.current_state == EntityState.ATTACK:
            self.entity.attack_behavior(world_state.player)
        elif self.current_state == EntityState.FLEE:
            self.entity.flee_behavior(world_state.player)
```

### Entity State Diagram
```
         ┌─────────────────────────────────────────┐
         │                                         │
         ▼                                         │
      [IDLE] ──────► [PATROL] ──────► [CHASE]     │
         │               │               │         │
         │               │               │         │
         │               ▼               ▼         │
         │           [DORMANT]       [ATTACK]      │
         │                              │         │
         │                              │         │
         │                              ▼         │
         │                           [FLEE] ──────┘
         │
         └──────────────────────────────────────────► [DEAD]
```

---

## Damage Calculation

### Physical Damage
```python
def calculate_physical_damage(attacker, defender, weapon):
    """
    Base damage formula.
    """
    # Base damage
    base_damage = weapon.damage
    
    # Strength bonus
    strength_bonus = attacker.stats.strength * 0.5
    
    # Weapon level multiplier
    weapon_multiplier = 1.0 + (weapon.level - 1) * 0.05
    
    # Enchantment bonus
    enchant_bonus = sum(e.value for e in weapon.enchantments if e.type == "physical_damage")
    
    # Rune bonus
    rune_bonus = sum(r.value for r in weapon.socketed_runes if r.type == "physical_damage")
    
    # Total attack power
    attack_power = (base_damage + strength_bonus + enchant_bonus + rune_bonus) * weapon_multiplier
    
    # Defense reduction
    defense = defender.stats.defense
    armor = defender.equipment.armor.defense if defender.equipment.armor else 0
    total_defense = defense + armor
    
    # Damage formula: attack * (100 / (100 + defense))
    reduction_factor = 100 / (100 + total_defense)
    final_damage = attack_power * reduction_factor
    
    # Critical hit check
    crit_chance = attacker.stats.agility * 0.01 + weapon.crit_chance
    if random.random() < crit_chance:
        final_damage *= 1.5
    
    return max(1, int(final_damage))
```

### Elemental Damage
```python
def calculate_elemental_damage(base_damage, element, attacker, defender):
    """
    Elemental damage with resistances.
    """
    # Element multiplier
    element_multipliers = {
        "fire": 1.0,
        "ice": 1.0,
        "lightning": 1.2,
        "poison": 0.8,
        "shadow": 1.1,
        "holy": 0.9
    }
    
    # Attacker element bonus
    element_bonus = attacker.stats.elemental_power.get(element, 0)
    
    # Defender resistance
    resistance = defender.stats.resistances.get(element, 0) / 100
    
    # Calculate damage
    raw_damage = base_damage * element_multipliers.get(element, 1.0)
    raw_damage += element_bonus
    final_damage = raw_damage * (1 - resistance)
    
    return max(1, int(final_damage))
```

---

## XP & Leveling System

### XP Requirements
```python
def xp_required_for_level(level):
    """
    XP needed to reach next level.
    Formula: base * level^1.5
    """
    base_xp = 100
    return int(base_xp * (level ** 1.5))

# Level 1→2: 100 XP
# Level 2→3: 283 XP
# Level 5→6: 1118 XP
# Level 10→11: 3162 XP
# Level 20→21: 8944 XP
```

### XP Gain Sources
```python
def calculate_xp_gain(source, source_level, player_level):
    """
    XP gain based on source and level difference.
    """
    base_xp = {
        "kill": 50,
        "quest": 200,
        "craft": 30,
        "explore": 10,
        "mine": 15,
        "enchant": 50,
        "boss": 1000
    }
    
    # Level difference modifier
    level_diff = source_level - player_level
    if level_diff > 0:
        modifier = 1.0 + (level_diff * 0.1)  # Bonus for harder content
    else:
        modifier = max(0.1, 1.0 + (level_diff * 0.05))  # Reduced for easier content
    
    return int(base_xp.get(source, 0) * modifier)
```

### Weapon XP
```python
def weapon_xp_gain(weapon, combat_xp):
    """
    Weapons gain XP from combat usage.
    """
    xp_multiplier = {
        "common": 1.0,
        "uncommon": 0.9,
        "rare": 0.8,
        "epic": 0.7,
        "legendary": 0.6
    }
    
    return int(combat_xp * xp_multiplier.get(weapon.rarity, 1.0))
```

---

## Trap Detection & Disarm

### Detection Formula
```python
def detect_trap(player, trap_block):
    """
    Chance to detect hidden traps.
    """
    base_chance = 0.3
    
    # Perception bonus
    perception_bonus = player.stats.perception * 0.02
    
    # Skill bonus
    skill_bonus = player.skills.get("perception", {}).get("level", 0) * 0.05
    
    # Equipment bonus (e.g., "Keen Eye" perk)
    equip_bonus = 0.1 if "keen_eye" in player.perks else 0
    
    # Trap difficulty penalty
    difficulty_penalty = trap_block.trap.get("disarm_difficulty", 0.5)
    
    total_chance = base_chance + perception_bonus + skill_bonus + equip_bonus - difficulty_penalty
    
    return max(0.05, min(0.95, total_chance))
```

### Disarm Formula
```python
def disarm_trap(player, trap_block):
    """
    Chance to successfully disarm a detected trap.
    """
    base_chance = 0.5
    
    # Relevant skill (perception, agility, or crafting based on trap type)
    skill_name = trap_block.trap.get("disarm_skill", "perception")
    skill_level = player.skills.get(skill_name, {}).get("level", 0)
    skill_bonus = skill_level * 0.05
    
    # Agility bonus for physical traps
    agility_bonus = player.stats.agility * 0.01
    
    # Intelligence bonus for magical traps
    intelligence_bonus = player.stats.intelligence * 0.01 if "magical" in trap_block.trap.get("types", []) else 0
    
    # Trap difficulty
    difficulty = trap_block.trap.get("disarm_difficulty", 0.5)
    
    total_chance = base_chance + skill_bonus + agility_bonus + intelligence_bonus - difficulty
    
    return max(0.05, min(0.95, total_chance))
```

---

## Weather Effects on Gameplay

### Weather State Machine
```python
class WeatherSystem:
    def __init__(self):
        self.states = {
            "clear": {"transition_chances": {"rain": 0.1, "fog": 0.05}},
            "rain": {"transition_chances": {"clear": 0.2, "storm": 0.1}},
            "storm": {"transition_chances": {"rain": 0.3, "clear": 0.1}},
            "fog": {"transition_chances": {"clear": 0.15, "rain": 0.05}},
            "blizzard": {"transition_chances": {"snow": 0.3, "clear": 0.05}},
            "ashfall": {"transition_chances": {"clear": 0.2, "eruption": 0.05}}
        }
        self.current = "clear"
    
    def update(self, biome):
        """Update weather based on biome and random chance."""
        chances = self.states[self.current]["transition_chances"]
        
        # Filter valid transitions for biome
        valid = {k: v for k, v in chances.items() if self.is_valid_for_biome(k, biome)}
        
        # Roll for transition
        roll = random.random()
        cumulative = 0
        for state, chance in valid.items():
            cumulative += chance
            if roll < cumulative:
                self.current = state
                return
        
        # No transition, stay in current state
```

### Weather Effects
```python
def apply_weather_effects(player, weather, biome):
    """
    Apply weather-based effects to player.
    """
    effects = []
    
    if weather == "blizzard" and biome == "snow_forest":
        effects.append({"type": "frostbite", "damage_per_sec": 2})
        effects.append({"type": "slow", "value": 0.3})
        effects.append({"type": "visibility", "reduction": 0.3})
    
    elif weather == "ashfall" and biome == "volcano":
        effects.append({"type": "fire_damage", "damage_per_sec": 1})
        effects.append({"type": "visibility", "reduction": 0.2})
    
    elif weather == "sandstorm" and biome == "savana":
        effects.append({"type": "dehydration", "rate": 1.5})
        effects.append({"type": "visibility", "reduction": 0.5})
        effects.append({"type": "wind_damage", "damage_per_sec": 1})
    
    elif weather == "rain":
        effects.append({"type": "wetness", "increase": 0.5})
        effects.append({"type": "fire_resistance", "reduction": 0.2})
    
    return effects
```

---

## Karma System

### Karma Effects
```python
def calculate_karma_effect(player_karma):
    """
    Calculate spawn chances and NPC reactions based on karma.
    """
    effects = {
        "death_spawn_chance": 0.0001,
        "ghost_spawn_chance": 0.0,
        "shadow_spawn_chance": 0.0,
        "npc_disposition": "neutral",
        "shop_prices": 1.0,
        "quest_availability": 1.0
    }
    
    if player_karma < 20:
        effects["death_spawn_chance"] = 0.0005
        effects["ghost_spawn_chance"] = 0.3
        effects["shadow_spawn_chance"] = 0.5
        effects["npc_disposition"] = "hostile"
        effects["shop_prices"] = 1.3
        effects["quest_availability"] = 0.7
    
    elif player_karma < 40:
        effects["death_spawn_chance"] = 0.0002
        effects["ghost_spawn_chance"] = 0.1
        effects["shadow_spawn_chance"] = 0.2
        effects["npc_disposition"] = "suspicious"
        effects["shop_prices"] = 1.1
        effects["quest_availability"] = 0.9
    
    elif player_karma > 80:
        effects["death_spawn_chance"] = 0.00001
        effects["ghost_spawn_chance"] = 0.0
        effects["shadow_spawn_chance"] = 0.05
        effects["npc_disposition"] = "friendly"
        effects["shop_prices"] = 0.85
        effects["quest_availability"] = 1.2
    
    return effects

def modify_karma(player, action):
    """
    Modify karma based on player actions.
    """
    karma_changes = {
        "kill_innocent": -10,
        "kill_monster": +5,
        "complete_quest": +10,
        "help_npc": +8,
        "steal": -15,
        "pay_debt": +5,
        "break_law": -20,
        "donate": +7,
        "betray_quest": -25
    }
    
    player.stats.karma += karma_changes.get(action, 0)
    player.stats.karma = max(0, min(100, player.stats.karma))
```

---

## Chunk Loading & Memory Management

### Chunk Priority System
```python
def calculate_chunk_priority(chunk_pos, player_pos, render_distance):
    """
    Priority for chunk loading. Closer = higher priority.
    """
    dx = abs(chunk_pos[0] - player_pos[0])
    dy = abs(chunk_pos[1] - player_pos[1])
    distance = dx + dy  # Manhattan distance
    
    if distance > render_distance:
        return 0  # Don't load
    
    # Priority: closer chunks loaded first
    priority = render_distance - distance
    
    # Boost priority for chunks with entities
    if chunk_has_entities(chunk_pos):
        priority += 2
    
    # Boost priority for chunks with buildings
    if chunk_has_building(chunk_pos):
        priority += 3
    
    return priority

def manage_chunk_loading(player_pos, loaded_chunks, render_distance):
    """
    Load/unload chunks based on player position.
    """
    target_chunks = get_visible_chunks(player_pos, render_distance)
    
    # Chunks to load
    to_load = [c for c in target_chunks if c not in loaded_chunks]
    
    # Chunks to unload
    to_unload = [c for c in loaded_chunks if c not in target_chunks]
    
    # Sort by priority
    to_load.sort(key=lambda c: calculate_chunk_priority(c, player_pos, render_distance), reverse=True)
    
    return to_load, to_unload
```

---

## Crafting System

### Recipe Validation
```python
def can_craft(player, recipe):
    """
    Check if player has materials and skill for crafting.
    """
    # Check materials
    for ingredient in recipe["materials"]:
        if not player.inventory.has_item(ingredient["item_id"], ingredient["qty"]):
            return False
    
    # Check skill requirement
    if "skill_requirement" in recipe:
        for skill, level in recipe["skill_requirement"].items():
            if player.skills.get(skill, {}).get("level", 0) < level:
                return False
    
    # Check level requirement
    if "level_requirement" in recipe:
        if player.level < recipe["level_requirement"]:
            return False
    
    # Check crafting station
    if "station" in recipe:
        if not player.near_station(recipe["station"]):
            return False
    
    return True

def craft_item(player, recipe):
    """
    Craft item and consume materials.
    """
    if not can_craft(player, recipe):
        return None
    
    # Consume materials
    for ingredient in recipe["materials"]:
        player.inventory.remove_item(ingredient["item_id"], ingredient["qty"])
    
    # Calculate quality based on skill
    crafting_skill = player.skills.get("crafting", {}).get("level", 0)
    base_quality = recipe.get("base_quality", 1.0)
    quality = base_quality + (crafting_skill * 0.02)
    
    # Masterwork chance
    masterwork_chance = recipe.get("masterwork_chance", 0.05) + (crafting_skill * 0.01)
    is_masterwork = random.random() < masterwork_chance
    
    if is_masterwork:
        quality *= 1.2
    
    # Create item
    item = create_item(recipe["output"], quality=quality)
    
    # Gain XP
    xp_gain = recipe.get("xp", 30)
    player.gain_xp("crafting", xp_gain)
    
    return item
```

---

## Combat Formulas

### Hit Chance
```python
def calculate_hit_chance(attacker, defender):
    """
    Chance to land a hit.
    """
    base_chance = 0.8
    
    # Attacker agility bonus
    attacker_bonus = attacker.stats.agility * 0.01
    
    # Defender agility penalty
    defender_penalty = defender.stats.agility * 0.005
    
    # Weapon speed bonus
    weapon_speed = attacker.equipment.weapon.speed if attacker.equipment.weapon else 1.0
    speed_bonus = (weapon_speed - 1.0) * 0.1
    
    hit_chance = base_chance + attacker_bonus - defender_penalty + speed_bonus
    
    return max(0.1, min(0.95, hit_chance))
```

### Dodge Chance
```python
def calculate_dodge_chance(defender, attacker):
    """
    Chance to dodge an attack.
    """
    base_chance = 0.1
    
    # Agility bonus
    agility_bonus = defender.stats.agility * 0.015
    
    # Perception bonus (see attack coming)
    perception_bonus = defender.stats.perception * 0.005
    
    # Stealth bonus (if attacker is stealthed)
    if attacker.is_stealthed:
        stealth_penalty = 0.2
    else:
        stealth_penalty = 0
    
    dodge_chance = base_chance + agility_bonus + perception_bonus - stealth_penalty
    
    return max(0.0, min(0.5, dodge_chance))
```

### Damage Formula (Complete)
```python
def calculate_damage(attacker, defender, weapon=None):
    """
    Complete damage calculation.
    """
    if weapon is None:
        weapon = attacker.equipment.weapon
    
    # Hit check
    if random.random() > calculate_hit_chance(attacker, defender):
        return {"hit": False, "damage": 0, "type": "miss"}
    
    # Dodge check
    if random.random() < calculate_dodge_chance(defender, attacker):
        return {"hit": True, "damage": 0, "type": "dodge"}
    
    # Base damage
    base_damage = weapon.damage if weapon else attacker.stats.strength * 0.5
    
    # Strength modifier
    strength_mod = 1.0 + (attacker.stats.strength * 0.02)
    
    # Weapon level modifier
    weapon_level_mod = 1.0 + (weapon.level - 1) * 0.05 if weapon else 1.0
    
    # Enchantment modifiers
    enchant_mod = 1.0
    if weapon:
        for enchant in weapon.enchantments:
            if enchant.type == "damage_multiplier":
                enchant_mod += enchant.value
    
    # Rune modifiers
    rune_mod = 1.0
    if weapon:
        for rune in weapon.socketed_runes:
            if rune.type == "damage_multiplier":
                rune_mod += rune.value
    
    # Calculate raw damage
    raw_damage = base_damage * strength_mod * weapon_level_mod * enchant_mod * rune_mod
    
    # Defense reduction
    defense = defender.stats.defense
    armor_defense = defender.equipment.armor.defense if defender.equipment.armor else 0
    total_defense = defense + armor_defense
    
    reduction = 100 / (100 + total_defense)
    final_damage = raw_damage * reduction
    
    # Critical hit
    crit_chance = attacker.stats.agility * 0.005
    is_crit = random.random() < crit_chance
    if is_crit:
        final_damage *= 1.5
    
    # Elemental damage
    elemental_damage = 0
    if weapon:
        for enchant in weapon.enchantments:
            if enchant.type in ["fire_damage", "ice_damage", "lightning_damage"]:
                elemental_damage += calculate_elemental_damage(
                    enchant.value,
                    enchant.type.replace("_damage", ""),
                    attacker,
                    defender
                )
    
    total_damage = int(final_damage + elemental_damage)
    
    return {
        "hit": True,
        "damage": max(1, total_damage),
        "type": "crit" if is_crit else "normal",
        "elemental": elemental_damage
    }
```

---

## Inventory Management

### Weight System
```python
def calculate_inventory_weight(player):
    """
    Calculate total inventory weight.
    """
    total_weight = 0
    
    for item in player.inventory.items:
        total_weight += item.weight * item.qty
    
    return total_weight

def can_carry_more(player, item, qty=1):
    """
    Check if player can carry more items.
    """
    current_weight = calculate_inventory_weight(player)
    item_weight = item.weight * qty
    max_weight = player.stats.endurance * 5 + 50  # Base 50 + 5 per endurance
    
    return (current_weight + item_weight) <= max_weight
```

### Stack Management
```python
def add_to_inventory(player, item, qty=1):
    """
    Add item to inventory with stacking.
    """
    if not can_carry_more(player, item, qty):
        return False, "Inventory full"
    
    if item.stackable:
        # Find existing stack
        for slot in player.inventory.slots:
            if slot.item_id == item.item_id and slot.qty < item.max_stack:
                space = item.max_stack - slot.qty
                to_add = min(qty, space)
                slot.qty += to_add
                qty -= to_add
                
                if qty <= 0:
                    return True, "Added to existing stack"
    
    # Create new slot(s)
    while qty > 0:
        new_qty = min(qty, item.max_stack if item.stackable else 1)
        player.inventory.slots.append(InventorySlot(item=item, qty=new_qty))
        qty -= new_qty
    
    return True, "Added to inventory"
```

---

## Quest System

### Quest States
```python
class QuestState(Enum):
    NOT_STARTED = "not_started"
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
```

### Quest Completion Check
```python
def check_quest_completion(player, quest):
    """
    Check if quest objectives are met.
    """
    for objective in quest.objectives:
        if objective.type == "kill":
            if player.kill_count.get(objective.target, 0) < objective.qty:
                return False
        
        elif objective.type == "collect":
            if player.inventory.count(objective.item_id) < objective.qty:
                return False
        
        elif objective.type == "deliver":
            if not player.has_delivered(objective.item_id, objective.target_npc):
                return False
        
        elif objective.type == "explore":
            if objective.chunk not in player.explored_chunks:
                return False
        
        elif objective.type == "talk":
            if not player.has_talked_to(objective.npc_id):
                return False
    
    return True

def complete_quest(player, quest):
    """
    Complete quest and grant rewards.
    """
    if not check_quest_completion(player, quest):
        return False
    
    # Grant XP
    player.gain_xp("quest", quest.xp_reward)
    
    # Grant items
    for item_reward in quest.item_rewards:
        add_to_inventory(player, item_reward["item_id"], item_reward["qty"])
    
    # Grant gold
    player.gold += quest.gold_reward
    
    # Modify karma
    if quest.karma_reward:
        player.stats.karma += quest.karma_reward
    
    # Unlock next quest
    if quest.next_quest:
        player.available_quests.append(quest.next_quest)
    
    quest.state = QuestState.COMPLETED
    return True
```
