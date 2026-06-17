# Core Architecture

## 1. Distance Calculations — Dijkstra on Weighted Graph
- **Dijkstra** for shortest-path distance calculations across the world graph.
- Each block has a **weight** (like Minecraft) that affects traversal cost.

**Examples:**
```json
// Weighted path costs: grass=1, stone=1.2, gravel=1.5
// Path from (0,0) to (3,0): grass+stone+gravel = 1 + 1.2 + 1.5 = 3.7 cost
```

## 2. Agent System — LangGraph
- **LangGraph** for orchestrating NPC/AI agent behaviors and state transitions.

**Examples:**
```python
# Agent state machine: idle -> patrol -> detect_player -> combat -> idle
# Each node in the LangGraph represents an agent behavior state
```

## 3. State Machines
- State-machine checks for game logic (player states, block states, entity AI).

**Examples:**
```python
# Player: { idle, walking, running, mining, crafting, sleeping, dead }
# Block: { intact, damaged, broken, destroyed }
# Monster: { dormant, patrolling, chasing, attacking, fleeing }
```

## 4. Shared State — Redis (Upstash)
- **Redis Upstash** for shared state between users and the AI server.
- JSON Upstash for simple JSON-based state changes.

**Examples:**
```python
# redis.set(f"player:{player_id}:position", json.dumps({"x": 5, "y": 12, "depth": 0}))
# redis.set(f"chunk:{chunk_x}:{chunk_y}", json.dumps(chunk_data))
```

## 5. Weight-Based Movement
- Movement calculated via Dijkstra using per-block weights.
- Weights account for terrain difficulty, hazards, and monster resistances.

**Examples:**
```json
// Lava weight = 200 / monster_fire_resistance
// Water weight = 100 / monster_water_resistance
```

## 6. Fully Customizable Blocks & Items (JSON Maps)
Every block and item is defined as a JSON map — fully data-driven, no hardcoding.

### Block Schema
```json
{
  "x": 3,
  "y": 15,
  "depth": 2,
  "trap": true,
  "biome": "savana",
  "items": [],
  "block_id": "b-grass-001",
  "weight": 1.0,
  "durability": {
    "current": 0,
    "max": 0,
    "mining_threshold": 0
  },
  "entities": [],
  "physics": {
    "temperature": 0,
    "wetness": 0,
    "fire_resistance": 0,
    "electricity_resistance": 0,
    "air_resistance": 0,
    "shock_resistance": 0,
    "melt_temperature": 0
  }
}
```

**Example — Grass Block:**
```json
{
  "x": 10,
  "y": 5,
  "depth": 0,
  "block_id": "b-grass-001",
  "biome": "plain",
  "weight": 1.0,
  "durability": { "current": 5, "max": 5, "mining_threshold": 1 },
  "trap": { "is_trap": false, "is_hidden": false, "trigger_weight_capacity": 0, "leads_to_depth": 0 },
  "items": [],
  "entities": [],
  "physics": { "temperature": 25, "wetness": 30, "fire_resistance": 5, "electricity_resistance": -1, "air_resistance": 20, "shock_resistance": 0, "melt_temperature": 200 }
}
```

**Example — Volcano Trap (Hidden Hole):**
```json
{
  "x": 3,
  "y": 15,
  "depth": -2,
  "block_id": "b-lava-trap-001",
  "biome": "volcano",
  "weight": 16.5,
  "durability": { "current": 30, "max": 30, "mining_threshold": 10 },
  "trap": {
    "is_trap": true,
    "is_hidden": true,
    "trigger_weight_capacity": 80,
    "leads_to_depth": -20,
    "trigger_effect": "lava_pool",
    "damage_on_trigger": 50,
    "delay_seconds": 0.5,
    "disarm_skill": "perception",
    "disarm_difficulty": 0.7
  },
  "items": [
    { "item_id": "i-iron-sword", "name": "Rusted Iron Sword", "qty": 1 }
  ],
  "entities": [
    { "entity_id": "e-giant-01", "type": "monster", "name": "Fire Giant", "hp": 450, "weight": 500 }
  ],
  "physics": { "temperature": 120, "wetness": 0, "fire_resistance": 90, "electricity_resistance": 10, "air_resistance": 0, "shock_resistance": 40, "melt_temperature": 800 }
}
```

**Example — Snow Forest Trap (Frozen Lake):**
```json
{
  "x": 8,
  "y": 22,
  "depth": -1,
  "block_id": "b-ice-lake-001",
  "biome": "snow_forest",
  "weight": 0.8,
  "durability": { "current": 15, "max": 15, "mining_threshold": 5 },
  "trap": {
    "is_trap": true,
    "is_hidden": false,
    "trigger_weight_capacity": 50,
    "leads_to_depth": -15,
    "trigger_effect": "ice_break",
    "damage_on_trigger": 20,
    "delay_seconds": 0,
    "status_effect": { "type": "frozen", "duration": 5, "slow_percentage": 0.8 }
  },
  "items": [],
  "entities": [],
  "physics": { "temperature": -10, "wetness": 90, "fire_resistance": 0, "electricity_resistance": 30, "air_resistance": 5, "shock_resistance": 20, "melt_temperature": 0 }
}
```

**Example — Savana Trap (Quicksand):**
```json
{
  "x": 12,
  "y": 7,
  "depth": 0,
  "block_id": "b-quicksand-001",
  "biome": "savana",
  "weight": 5.0,
  "durability": { "current": 10, "max": 10, "mining_threshold": 0 },
  "trap": {
    "is_trap": true,
    "is_hidden": true,
    "trigger_weight_capacity": 30,
    "leads_to_depth": -8,
    "trigger_effect": "sinking",
    "damage_on_trigger": 0,
    "delay_seconds": 2,
    "escape_skill": "athletics",
    "escape_difficulty": 0.6,
    "status_effect": { "type": "restrained", "duration": 10, "slow_percentage": 1.0 }
  },
  "items": [],
  "entities": [],
  "physics": { "temperature": 45, "wetness": 5, "fire_resistance": 0, "electricity_resistance": -1, "air_resistance": 15, "shock_resistance": 0, "melt_temperature": 300 }
}
```

---

# Buildings System

Buildings are **chunk-based structures** that bypass normal block rendering:
- A house = 2×2 chunks. Instead of loading 2×2 chunks of individual blocks, the entire house is loaded as a single structure.
- **When outside:** only the house exterior/stub is shown.
- **When entering:** chunks switch scope — only the interior blocks are loaded.

**Example — Blacksmith:**
```json
{
  "building_id": "bld-blacksmith-001",
  "type": "functional",
  "occupies_chunks": [{ "x": 5, "y": 3 }, { "x": 6, "y": 3 }, { "x": 5, "y": 4 }, { "x": 6, "y": 4 }],
  "entrance": { "x": 5, "y": 3, "depth": 0 },
  "interior_chunk_id": "int-blacksmith-001",
  "npcs": ["e-blacksmith-01", "e-worker-blacksmith-01", "e-worker-blacksmith-02"],
  "crafting_stations": ["furnace", "anvil", "grindstone", "hammer", "blacksmith-set"],
  "ambience": { "sound": "forge_hammering", "music": "blacksmith_theme", "lighting": "warm_glow" },
  "weather_protection": 1.0,
  "security_level": 2,
  "building_quality": "sturdy",
  "decay_rate": 0.01,
  "lore": "The Ironhand Forge has stood for three generations. The walls bear scorch marks from a thousand blades."
}
```

**Example — Tavern:**
```json
{
  "building_id": "bld-tavern-001",
  "type": "social",
  "occupies_chunks": [{ "x": 10, "y": 5 }, { "x": 11, "y": 5 }, { "x": 10, "y": 6 }, { "x": 11, "y": 6 }],
  "entrance": { "x": 10, "y": 5, "depth": 0 },
  "interior_chunk_id": "int-tavern-001",
  "npcs": ["e-barkeep-01", "e-bard-01", "e-trader-02"],
  "services": ["rest", "food", "drink", "information", "trade"],
  "ambience": { "sound": "crowd_chatter", "music": "tavern_theme", "lighting": "candlelight" },
  "weather_protection": 1.0,
  "building_quality": "weathered",
  "decay_rate": 0.005,
  "lore": "The Drunken Dragon. Where stories are born and secrets are sold."
}
```

**Example — Player-Built Shelter:**
```json
{
  "building_id": "bld-shelter-player-001",
  "type": "player_built",
  "occupies_chunks": [{ "x": 2, "y": 2 }],
  "entrance": { "x": 2, "y": 2, "depth": 0 },
  "interior_chunk_id": "int-shelter-001",
  "npcs": [],
  "owner": "p-player-001",
  "crafting_stations": ["workbench"],
  "storage": [
    { "container_id": "chest-01", "capacity": 20, "items": [] }
  ],
  "ambience": { "sound": "wind_outside", "lighting": "dim" },
  "weather_protection": 0.7,
  "building_quality": "makeshift",
  "decay_rate": 0.05,
  "upgrades_available": ["stone_walls", "reinforced_door", "roof", "bed"],
  "lore": "A humble start. Every great fortress began with four walls and a roof."
}
```

**Example — Enter Flow:**
```
1. Player at (4,3) approaches building at chunks (5,3)-(6,4)
2. Player reaches entrance at (5,3)
3. Unload exterior chunks (5,3)-(6,4)
4. Load interior chunk "int-blacksmith-001" (4x4 interior blocks)
5. Player position → interior entrance coords
6. On exit: reverse the swap
```

---

# Entities System

## 1. Player
Stats: health, hunger, thirst, stamina, equipment, inventory, skills, karma, sleep.

**Example:**
```json
{
  "entity_id": "p-player-001",
  "type": "player",
  "level": 7,
  "xp": 2450,
  "xp_to_next_level": 3200,
  "xp_total": 8900,
  "stat_points": 5,
  "skill_points": 2,
  "stats": {
    "health": 100,
    "max_health": 100,
    "hunger": 80,
    "thirst": 60,
    "sleep": 90,
    "tiredness": 10,
    "karma": 50,
    "strength": 12,
    "agility": 8,
    "intelligence": 6,
    "endurance": 10,
    "perception": 7,
    "charisma": 5
  },
  "equipment": {
    "weapon": "i-shadow-dagger",
    "armor": { "chest": "i-iron-chestplate", "legs": "i-leather-leggings", "boots": "i-leather-boots" },
    "accessory": "i-iron-amulet"
  },
  "rune_slots": {
    "weapon": { "total": 2, "filled": 1, "runes": ["r-flame-01"] },
    "armor": { "total": 1, "filled": 0, "runes": [] }
  },
  "position": { "x": 5, "y": 10, "depth": 0 },
  "skills": {
    "combat": { "level": 3, "xp": 450, "xp_next": 800, "stat_bonus": { "damage": 6, "crit_chance": 0.05 } },
    "mining": { "level": 1, "xp": 120, "xp_next": 300, "stat_bonus": { "mining_speed": 0.1 } },
    "crafting": { "level": 2, "xp": 280, "xp_next": 500, "stat_bonus": { "craft_quality": 0.08 } },
    "stealth": { "level": 0, "xp": 0, "xp_next": 100, "stat_bonus": {} },
    "alchemy": { "level": 0, "xp": 0, "xp_next": 100, "stat_bonus": {} },
    "enchanting": { "level": 1, "xp": 50, "xp_next": 200, "stat_bonus": { "enchant_power": 0.05 } }
  },
  "perks": ["iron_stomach", "keen_eye"],
  "status_effects": [],
  "inventory_weight_current": 12.5,
  "inventory_weight_max": 50.0,
  "death_count": 0,
  "play_time_seconds": 7200,
  "biome_history": ["plain", "volcano"],
  "achievements": ["first_kill", "first_craft"]
}
```

## 2. Mobs
Passive animals: cows, pigs, rabbits, sheep, chickens, horses.

**Example:**
```json
{
  "entity_id": "e-cow-042",
  "type": "mob",
  "name": "Cow",
  "hp": 20,
  "behavior": "wander",
  "senses": { "sight": 5, "hearing": 4, "smell": 3 },
  "tamable": true,
  "tamable_item": "i-wheat",
  "drops": [
    { "item_id": "i-raw-beef", "qty": 3, "chance": 1.0 },
    { "item_id": "i-leather", "qty": 1, "chance": 0.8 },
    { "item_id": "i-bone", "qty": "1d2", "chance": 0.3 }
  ],
  "biome_spawns": ["plain", "savana"],
  "herd_behavior": { "min": 3, "max": 8 },
  "flee_from": ["monster", "player_attack"],
  "lore": "A gentle creature. Its leather is prized by blacksmiths."
}
```

## 3. Monsters
Hostile creatures: skeleton, goblins, cave crawlers, spiders, watchers, wolves.

**Example — Skeleton Archer:**
```json
{
  "entity_id": "e-skeleton-007",
  "type": "monster",
  "name": "Skeleton Archer",
  "hp": 40,
  "damage": 12,
  "range": 8,
  "behavior": "patrol",
  "senses": { "sight": 10, "hearing": 6, "smell": 0 },
  "aggression": 0.7,
  "flee_threshold": 0.2,
  "loot_table": [
    { "item_id": "i-bone", "qty": "1d4", "chance": 0.8 },
    { "item_id": "i-bow", "chance": 0.15 },
    { "item_id": "i-rusty-arrow", "qty": "2d4", "chance": 0.5 }
  ],
  "biome_spawns": ["volcano", "deepslate", "snow_forest"],
  "time_spawn": ["night", "dusk"],
  "pack_behavior": { "min": 2, "max": 5, "formation": "loose" },
  "lore": "Once a royal guard, now condemned to patrol the volcanic passages for eternity."
}
```

**Example — Cave Crawler:**
```json
{
  "entity_id": "e-cave-crawler-01",
  "type": "monster",
  "name": "Cave Crawler",
  "hp": 25,
  "damage": 8,
  "range": 1,
  "behavior": "ambush",
  "senses": { "sight": 3, "hearing": 12, "smell": 8 },
  "aggression": 0.9,
  "flee_threshold": 0.0,
  "special_traits": ["web_slinger", "ceiling_clinger", "poison_bite"],
  "status_effects": [
    { "type": "poison", "damage_per_sec": 2, "duration": 8 }
  ],
  "biome_spawns": ["deepslate", "volcano"],
  "habitat": "caves",
  "drops": [
    { "item_id": "i-crawler-silk", "qty": "1d3", "chance": 0.6 },
    { "item_id": "i-venom-sac", "qty": 1, "chance": 0.3 }
  ],
  "lore": "Blind but deadly. It feels your footsteps through the stone."
}
```

**Example — Fire Giant (Volcano Elite):**
```json
{
  "entity_id": "e-giant-01",
  "type": "monster",
  "subtype": "elite",
  "name": "Fire Giant",
  "hp": 450,
  "damage": 65,
  "range": 3,
  "behavior": "guardian",
  "senses": { "sight": 15, "hearing": 10, "smell": 12 },
  "aggression": 0.95,
  "flee_threshold": 0.0,
  "weight": 500,
  "special_traits": ["fire_aura", "ground_slam", "lava游泳"],
  "resistances": { "fire": 90, "physical": 40, "ice": 0.5 },
  "weaknesses": { "water": 2.0, "frost": 1.5 },
  "biome_spawns": ["volcano"],
  "habitat": "lava_caves",
  "drops": [
    { "item_id": "i-infernal-core", "qty": 1, "chance": 1.0 },
    { "item_id": "i-giant-bone", "qty": "2d3", "chance": 0.7 },
    { "item_id": "i-molten-sword", "qty": 1, "chance": 0.2 }
  ],
  "lore": "Ancient being of living flame. The volcano is its body, the lava its blood."
}
```

## 4. Workers
Functional NPCs: blacksmith, farmer, builder, baker, cook.

**Example — Blacksmith:**
```json
{
  "entity_id": "e-blacksmith-01",
  "type": "worker",
  "name": "Hrogir Ironhand",
  "profession": "blacksmith",
  "location": "bld-blacksmith-001",
  "trades": [
    { "offer": { "item_id": "i-iron-sword", "qty": 1 }, "cost": { "item_id": "i-gold", "qty": 5 } },
    { "offer": { "item_id": "i-iron-chestplate", "qty": 1 }, "cost": { "item_id": "i-gold", "qty": 12 } },
    { "offer": { "item_id": "i-steel-ingot", "qty": 3 }, "cost": { "item_id": "i-iron-ingot", "qty": 5 } }
  ],
  "experience": "journeyman",
  "quests": ["q-deliver-iron-ore", "q-smelt-steel"],
  "wage_per_hour": 20,
  "reputation": { "ironhold": 65, "general": 40 },
  "mood": "neutral",
  "specialization": ["weapons", "armor"],
  "quality_bonus": 0.15,
  "lore": "Third-generation blacksmith. His grandfather forged the legendary 'Embercleave'."
}
```

## 5. Citizens & Traders
Quest-givers and merchants with trade routes, gold exchange, and special wares.

**Example — Merchant:**
```json
{
  "entity_id": "e-merchant-03",
  "type": "trader",
  "name": "Elena Faircoin",
  "trades": [
    { "offer": { "item_id": "i-map-ancient-ruins", "qty": 1 }, "cost": 200 },
    { "offer": { "item_id": "i-health-potion", "qty": 3 }, "cost": 120 },
    { "offer": { "item_id": "i-enchanted-amulet", "qty": 1 }, "cost": 500, "stock": 1 }
  ],
  "quests": ["q-find-lost-artifact", "q-deliver-supplies"],
  "reputation": { "ironhold": 70, "general": 55 },
  "haggling_skill": 0.8,
  "inventory_refresh_hours": 24,
  "special_wares": ["rare_materials", "maps", "enchanted_items"],
  "trade_history": [],
  "lore": "Elena knows every merchant in the realm. Cross her, and you'll find no one willing to trade with you."
}
```

## 6. Hallucinations
Special characters that appear when player stats are critically low (high hunger, high thirst, low sleep, high tiredness).

**Examples:**
| Trigger | Hallucination | Effect |
|---------|---------------|--------|
| Hunger > 90 | "Ghost Feast" — visions of food that vanish when approached | Drains stamina |
| Thirst > 90 | "Water Mirage" — fake water sources | Player runs toward it, wastes energy |
| Tiredness > 80 | "Shadow Figures" — peripheral movement that isn't real | Confusion/debuff |
| Sleep < 20 | "Whispers" — audio hallucinations, fake entity markers | Map shows false enemy markers |

**Example — Hallucination:**
```json
{
  "entity_id": "e-hallucination-hunger-01",
  "type": "hallucination",
  "trigger_condition": { "stat": "hunger", "above": 90 },
  "appearance": "feast_table",
  "behavior": "appears_at_distance_15", "vanishes_on_approach",
  "duration_seconds": 30,
  "intensity": 0.8,
  "visual_distortion": { "blur": 0.3, "color_shift": "warm" },
  "sound_effects": ["sizzling_food", "clinking_glasses"],
  "lore": "The mind, starved, conjures what the body craves. A cruel trick of survival instinct."
}
```

## 7. Bosses
Elite monsters with wider range, higher damage, unique skills, and special effects.

**Example — The Infernal Colossus:**
```json
{
  "entity_id": "e-boss-001",
  "type": "boss",
  "name": "The Infernal Colossus",
  "hp": 5000,
  "speed": 4,
  "defense": 100,
  "body_type": "giant",
  "equipment": { "weapon": "i-infernal-sword", "armor": { "chest": "i-infernal-chestplate" } },
  "bounty": 1000,
  "loot": { "item_id": "i-infernal-sword", "qty": 1 },
  "fire_resistance": 30,
  "water_resistance": 80,
  "electric_resistance": 15,
  "poison_resistance": 60,
  "damage": 75,
  "range": 4,
  "skills": ["ground_slam", "lava_breath", "summon_minions"],
  "resistances": { "fire": 95, "physical": 50 },
  "weaknesses": { "water": 2.0 },
  "phase_triggers": [
    { "hp_below": 3000, "skill": "lava_breath", "cooldown": 10 },
    { "hp_below": 1000, "skill": "summon_minions", "cooldown": 30 }
  ],
  "loot_table": [
    { "item_id": "i-infernal-core", "qty": 1, "chance": 1.0 },
    { "item_id": "i-molten-sword", "qty": 1, "chance": 0.3 }
  ],
  "arena": { "type": "volcano_crater", "size_chunks": 4, "hazards": ["lava_geysers", "falling_rocks"] },
  "music": "boss_volcano_theme",
  "cutscene_on_spawn": "colossus_awakening",
  "lore": "Born from the first eruption, it sleeps beneath the magma. When the volcano stirs, the Colossus wakes."
}
```

## 8. Special Characters
Rare, high-impact entities tied to player karma.

| Entity | Trigger | Effect |
|--------|---------|--------|
| Death | 0.01% chance on any action | Appears suddenly and kills the player instantly |
| Shadow | Player has items in inventory | Demands an item; if refused, deals 50% max HP damage |
| Ghosts | Low karma zone | Reduces stats, applies negative effects (weakness, fatigue, confusion) |

**Karma System:**
- **Bad actions** (hurting characters, illegal acts) → lower karma → higher special-character spawn chances.
- **Good actions** (helping NPCs, completing quests) → higher karma → lower spawn chances.

**Examples:**
```json
// Player with low karma (karma < 20):
//   - Death spawn chance: 0.01% → 0.05%
//   - Ghost encounters: common in dungeons
//   - Shadow appears: when carrying any item
//
// Player with high karma (karma > 80):
//   - Death spawn chance: 0.01% → 0.001%
//   - Ghost encounters: never
//   - Shadow appears: only if carrying valuable items
```

**Special Character — Shadow:**
```json
{
  "entity_id": "e-shadow",
  "type": "special",
  "name": "Shadow",
  "behavior": {
    "trigger": "player_has_items",
    "demand": "random_item",
    "damage_on_refusal": { "type": "percent", "value": 50 }
  }
}
```
