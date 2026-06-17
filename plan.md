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
  "x": 3,                    // x-coordinate
  "y": 15,                   // y-coordinate
  "depth": 2,                // z-index (positive = above ground like +200 mountains, negative = holes like -2)
  "trap": true,             // e.g. a hole with depth -20 covered so enemies don't detect it; trap activates when stepped on
  "biome": "savana",         // e.g. savana, plain, volcano, snow forest, deepslate, etc. — unique temperatures and monsters
  "items": [],               // items on this block: sword, plants, armor, dead animal, etc.
  "block_id": "b-grass-001", // block UUID — every type has a unique ID: grass, stone, diamond, etc.
  "weight": 1.0,             // traversal cost: grass=1, stone=1.2, gravel=1.5, lava=200/monster_fire_resistance, water=100/monster_water_resistance
  "durability": {            // damage needed to break block (e.g. wooden fence needs 30 dmg); additional weight penalty; mining threshold determines if player can collect it
    "current": 0,
    "max": 0,
    "mining_threshold": 0
  },
  "entities": [],            // monsters, mobs, and other entities on this block
  "physics": {
    "temperature": 0,
    "wetness": 0,            // desert has dry air; pouring water changes wetness — affects traps, chemical reactions, etc.
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

# World System

## Chunk-Based World Rendering
The world is split into chunks. On each move, the player only sees **surrounding chunks** — 4 in each direction forming a diamond shape:

```
        -
    -------
  -----------
---------------
  -----------
    --------
        -
```

- Largest visible area at the 4 cardinal directions (up, down, left, right); diagonals have less.
- Each chunk = **4×4 blocks** = 16 blocks (2 blocks in each direction).

**Example — Chunk Coordinate System:**
```python
# Chunk (0,0) contains blocks where x=0..3, y=0..3
# Player at chunk (0,0) sees: chunks (-4..4, -4..4) in diamond pattern
# Only blocks within render distance are loaded into memory
```

## Fuzzy Logic for Transitions
Blocks and chunks follow **fuzzy logic** — abrupt transitions are unrealistic:
- Depth jumping from 0 to -20 in one block? Realistic for cliffs/mountains, but not for general terrain.
- Temperature jumping from 20°C to 130°C in one block? Not logical — smooth transitions enforced.

**Examples:**
```python
# Bad: depth[0]=0, depth[1]=-20  (sudden drop)
# Good: depth[0]=0, depth[1]=-2, depth[2]=-5, depth[3]=-10, depth[4]=-20 (gradual slope)
# 
# Bad: temp[0]=25, temp[1]=130  (sudden heat spike)
# Good: temp[0]=25, temp[1]=40, temp[2]=65, temp[3]=95, temp[4]=130 (volcano approach gradient)
```

## Entity Detection Beyond Render Distance
For long-range entities (sniper monsters, 5-6 chunks away):
- **Don't** scan/load the full chunk or render blocks.
- **Only** check entities in the distant graph — no block data needed.

**Examples:**
```python
# Sniper at chunk (10,5) — player at (0,0)
# Instead of loading all blocks in chunks 5-15:
#   entities_in_range = get_entities_in_radius(player_pos, radius_chunks=12)
#   for entity in entities_in_range:
#       if entity.has_trait("long_range"):
#           entity.attempt_attack(player)
#we use djkstra for entities that's it and update their distance
```

---

# Item System

Items are split into 13 categories:

| # | Category | Description | Example |
|---|----------|-------------|---------|
| 1 | **Functional Blocks** | Crafting/production stations | Furnaces, smokers, blast furnaces, alchemist lab blocks |
| 2 | **Furniture Blocks** | Decorative placeables | Chairs, tables, bookshelves |
| 3 | **Items** | Consumables and objects | Alcohol bottles, water bottles, food |
| 4 | **Weapons** | Combat equipment | Swords, bows, giant swords, staves, war picks, cleavers, scythes, flails, halberds, dual daggers |
| 5 | **Armor** | Protective gear | Chestplates, leggings, boots, hats, helmets, shields, bracers, pauldrons, cloaks, enchanted robes |
| 6 | **Clothing** | Cosmetic wear | Shirts, pants, robes, cloaks, capes, hoods, gloves, belts, amulets, rings |
| 7 | **Ruined Materials & Scraps** | Damaged item drops | Ruined fence → broken wood + nails (can be sold or recycled into lower-value materials) |
| 8 | **Agriculture** | Farming & botanicals | Crops, wheat, fertilizers, seeds |
| 9 | **Minerals** | Raw ores | Iron ore, coal ore, copper ore, silver ore, lead ore |
| 10 | **Alloys** | Smelted/refined minerals | Iron ingot, copper ingot, gold ingot, coal, charcoal, silver, lead |
| 11 | **Entity Loot** | Drops from mobs/monsters | Dead body, skeleton remains, monster equipment, blood, special materials |
| 12 | **Special Materials** | Rare crafting components | Dragon scales, enchanted crystals, void essence |
| 13 | **User Additions & Inventions** | Player-created content | Diagrams, electrical circuits, custom machines |
| 14 | **Runes** | Socketable modifiers | Flame runes, frost runes, void runes, soul runes, ward runes |
| 15 | **Enchantment Scrolls** | Enchantment recipes | Frost Brand scroll, Iron Skin scroll, Undying Flame scroll |

**Example — Item JSON:**
```json
{
  "item_id": "i-iron-sword",
  "name": "Rusted Iron Sword",
  "category": "weapons",
  "subcategory": "one-handed-sword",
  "level": 1,
  "level_requirement": 1,
  "xp": 0,
  "xp_to_next_level": 100,
  "stats": { "damage": 15, "speed": 1.2, "durability": 120 },
  "weight": 3.0,
  "value": 50,
  "craftable": true,
  "recipe": [{ "item_id": "i-iron-ingot", "qty": 2 }, { "item_id": "i-wood", "qty": 1 }],
  "damage": 15,
  "speed": 1.2,
  "durability": 120,
  "skills_compatibility": ["combat", "agility", "strength", "fast_strike", "fire_attack"],
  "crafting_time": 20,
  "rarity": "common",
  "masterwork_chance": 0.10,
  "enchantment_slots": 1,
  "rune_slots": 0,
  "condition": { "rust": 0.3, "sharpness": 0.6 },
  "upgrade_path": [
    { "level": 3, "stat_boost": { "damage": 3 }, "name": "Iron Sword" },
    { "level": 5, "stat_boost": { "damage": 8, "speed": 0.1 }, "name": "Sharpened Iron Sword" },
    { "level": 8, "stat_boost": { "damage": 15 }, "name": "Steel Sword", "recipe_upgrade": [{ "item_id": "i-steel-ingot", "qty": 2 }] }
  ],
  "lore": "Forged in the foundries of Ironhold, this blade has seen better days. A faint glow emanates from the pommel — remnants of an ancient enchantment."
}
```

**Example — Enhanced Weapon (Rare):**
```json
{
  "item_id": "i-shadow-dagger",
  "name": "Shadowfang Dagger",
  "category": "weapons",
  "subcategory": "dual-dagger",
  "level": 5,
  "level_requirement": 5,
  "xp": 320,
  "xp_to_next_level": 600,
  "stats": { "damage": 22, "speed": 2.5, "durability": 85 },
  "weight": 1.2,
  "value": 320,
  "craftable": false,
  "recipe": [],
  "skills_compatibility": ["assassination", "stealth", "poison", "backstab", "shadow_step"],
  "crafting_time": 0,
  "rarity": "rare",
  "masterwork_chance": 0.25,
  "enchantment_slots": 2,
  "rune_slots": 1,
  "socketed_runes": [],
  "condition": { "corruption": 0.15, "sharpness": 0.95 },
  "enchantments": [
    { "type": "life_steal", "tier": 1, "value": 0.08, "description": "Steals 8% of damage dealt as health" },
    { "type": "shadow_blade", "tier": 1, "value": 1, "description": "Attacks from stealth deal 2x damage" }
  ],
  "upgrade_path": [
    { "level": 7, "stat_boost": { "damage": 5, "speed": 0.2 }, "name": "Shadowfang Dagger+" },
    { "level": 10, "stat_boost": { "damage": 12, "speed": 0.3 }, "name": "Voidfang Dagger", "recipe_upgrade": [{ "item_id": "i-void-crystal", "qty": 3 }] },
    { "level": 15, "stat_boost": { "damage": 25 }, "name:": "Eclipse Fang", "enchantment_slots": 3, "rune_slots": 2 }
  ],
  "lore": "Carved from the fang of a void wyrm, this dagger drinks in the darkness. Those struck by it feel their warmth fade."
}
```

**Example — Armor (Chestplate):**
```json
{
  "item_id": "i-iron-chestplate",
  "name": "Iron Chestplate",
  "category": "armor",
  "subcategory": "chest",
  "level": 3,
  "level_requirement": 3,
  "xp": 0,
  "xp_to_next_level": 200,
  "stats": { "defense": 18, "durability": 200, "speed_penalty": 0.15 },
  "weight": 8.5,
  "value": 180,
  "craftable": true,
  "recipe": [{ "item_id": "i-iron-ingot", "qty": 5 }, { "item_id": "i-leather-strip", "qty": 3 }],
  "skills_compatibility": ["heavy_armor", "tank", "shield_bash", "iron_will"],
  "rarity": "common",
  "enchantment_slots": 1,
  "rune_slots": 1,
  "socketed_runes": [],
  "material_tier": 2,
  "biome_affinity": { "snow": 1.1, "volcano": 0.8 },
  "upgrade_path": [
    { "level": 5, "stat_boost": { "defense": 5 }, "name": "Iron Chestplate+" },
    { "level": 8, "stat_boost": { "defense": 12 }, "name": "Steel Chestplate", "recipe_upgrade": [{ "item_id": "i-steel-ingot", "qty": 5 }] },
    { "level": 12, "stat_boost": { "defense": 20 }, "name": "Mithril Chestplate", "rune_slots": 2 }
  ],
  "lore": "Standard-issue armor from the Ironhold garrison. Reliable, if a bit heavy."
}
```

**Example — Consumable (Potion):**
```json
{
  "item_id": "i-health-potion-sm",
  "name": "Lesser Healing Potion",
  "category": "items",
  "subcategory": "consumable",
  "stats": { "heal_amount": 30 },
  "weight": 0.5,
  "value": 25,
  "craftable": true,
  "recipe": [{ "item_id": "i-red-mushroom", "qty": 2 }, { "item_id": "i-clean-water", "qty": 1 }],
  "rarity": "common",
  "stackable": true,
  "max_stack": 20,
  "cooldown_seconds": 5,
  "effect_duration": 0,
  "biome_spoilage": { "volcano": 0.5, "snow_forest": 1.5 },
  "lore": "A small vial of crimson liquid. Tastes like burnt berries — but it works."
}
```

**Example — Functional Block (Furnace):**
```json
{
  "item_id": "b-furnace",
  "name": "Stone Furnace",
  "category": "functional_blocks",
  "subcategory": "smelting_station",
  "stats": { "smelt_speed": 1.0, "fuel_efficiency": 0.8 },
  "weight": 50.0,
  "value": 120,
  "craftable": true,
  "recipe": [{ "item_id": "i-cobblestone", "qty": 8 }],
  "rarity": "common",
  "placeable": true,
  "interior_only": false,
  "fuel_types": ["coal", "charcoal", "wood"],
  "smeltable_recipes": [
    { "input": "i-iron-ore", "output": "i-iron-ingot", "time": 10 },
    { "input": "i-copper-ore", "output": "i-copper-ingot", "time": 8 },
    { "input": "i-gold-ore", "output": "i-gold-ingot", "time": 15 }
  ],
  "lore": "A rough-hewn furnace. The soot marks tell stories of countless smelting sessions."
}
```

**Example — Ruined Material:**
```json
{
  "item_id": "i-ruined-wood",
  "name": "Broken Wood Planks",
  "category": "ruined_materials_and_scraps",
  "value": 2,
  "recycles_to": { "item_id": "i-wood-scraps", "qty": 3 }
}
```

**Example — Rune Item:**
```json
{
  "item_id": "i-rune-stone",
  "name": "Blank Rune Stone",
  "category": "runes",
  "subcategory": "crafting_component",
  "weight": 0.5,
  "value": 15,
  "craftable": true,
  "recipe": [{ "item_id": "i-obsidian", "qty": 2 }, { "item_id": "i-magic-essence", "qty": 1 }],
  "rarity": "common",
  "stackable": true,
  "max_stack": 20,
  "lore": "A smooth black stone, ready to be inscribed with a rune glyph."
}
```

**Example — Enchantment Scroll:**
```json
{
  "item_id": "i-scroll-frost-brand",
  "name": "Scroll of Frost Brand",
  "category": "enchantment_scrolls",
  "subcategory": "weapon_enchantment",
  "weight": 0.2,
  "value": 120,
  "craftable": false,
  "enchantment_granted": "ench-frost-brand",
  "level_requirement": 10,
  "skill_requirement": { "enchanting": 5 },
  "rarity": "rare",
  "stackable": false,
  "usable_at": ["enchanting_table", "enchanting_lab"],
  "lore": "The scroll radiates cold. Frost creeps across your fingers as you read the ancient runes."
}
```

---

# Rune System

Runes are socketable items that provide passive bonuses when placed in weapon/armor rune slots.

## Rune Types

| Type | Slot | Effect | Rarity Tiers |
|------|------|--------|--------------|
| **Flame** | Weapon | Adds fire damage | Lesser (5), Greater (15), Superior (30) |
| **Frost** | Weapon | Adds slow effect | Lesser (10%), Greater (25%), Superior (40%) |
| **Venom** | Weapon | Adds poison DOT | Lesser (2/s), Greater (5/s), Superior (10/s) |
| **Life** | Armor | Health regen | Lesser (1/s), Greater (3/s), Superior (6/s) |
| **Iron** | Armor | Defense boost | Lesser (+3), Greater (+8), Superior (+15) |
| **Swift** | Armor | Speed boost | Lesser (+5%), Greater (+12%), Superior (+20%) |
| **Void** | Weapon | Armor penetration | Lesser (5%), Greater (15%), Superior (25%) |
| **Ward** | Armor | Elemental resist | Lesser (10%), Greater (25%), Superior (40%) |
| **Soul** | Weapon | XP bonus | Lesser (+10%), Greater (+25%), Superior (+50%) |
| **Echo** | Weapon | Cooldown reduction | Lesser (5%), Greater (12%), Superior (20%) |

## Rune Properties

**Example — Rune (Common):**
```json
{
  "rune_id": "r-flame-01",
  "name": "Lesser Flame Rune",
  "type": "flame",
  "tier": "lesser",
  "slot": "weapon",
  "effect": {
    "type": "fire_damage",
    "value": 5,
    "proc_chance": 0.2,
    "description": "20% chance to deal 5 fire damage on hit"
  },
  "weight": 0.1,
  "value": 40,
  "craftable": true,
  "recipe": [{ "item_id": "i-fire-crystal-shard", "qty": 2 }, { "item_id": "i-rune-stone", "qty": 1 }],
  "stackable": true,
  "max_stack": 10,
  "lore": "A small stone etched with a flickering flame glyph. Warm to the touch."
}
```

**Example — Rune (Rare):**
```json
{
  "rune_id": "r-void-01",
  "name": "Greater Void Rune",
  "type": "void",
  "tier": "greater",
  "slot": "weapon",
  "effect": {
    "type": "armor_penetration",
    "value": 0.15,
    "description": "Ignores 15% of enemy armor"
  },
  "weight": 0.1,
  "value": 180,
  "craftable": false,
  "recipe": [],
  "stackable": false,
  "set_bonus": {
    "set_name": "Void Walker",
    "pieces": 2,
    "bonus": { "type": "shadow_damage", "value": 0.10, "description": "+10% shadow damage with 2 void runes" }
  },
  "lore": "Carved from a fragment of the Void itself. Reality bends around it."
}
```

## Rune Socketing Rules
- Weapons: max 2 rune slots (can be increased by masterwork or enchantment)
- Armor: max 1 rune slot per piece
- Runes cannot be removed once socketed (destroyed on extraction)
- Matching set runes provide bonus effects
- Rune quality scales with player enchanting skill

---

# Enchantment System

Enchantments are magical modifications applied to weapons/armor at enchanting stations.

## Enchantment Tiers

| Tier | Level Required | Materials | Power |
|------|----------------|-----------|-------|
| **Minor** | 1 | Enchanting Dust x5 | 0.8x base |
| **Lesser** | 5 | Enchanting Dust x10, Magic Essence x2 | 1.0x base |
| **Greater** | 10 | Enchanting Dust x20, Magic Essence x5, Crystal x1 | 1.5x base |
| **Superior** | 15 | Enchanting Dust x40, Magic Essence x10, Rare Crystal x1 | 2.0x base |
| **Legendary** | 20 | Enchanting Dust x80, Magic Essence x20, Legendary Crystal x1 | 3.0x base |

## Enchantment Types

### Weapon Enchantments

**Example — Weapon Enchantment:**
```json
{
  "enchantment_id": "ench-frost-brand",
  "name": "Frost Brand",
  "type": "weapon",
  "tier": "greater",
  "level_requirement": 10,
  "skill_requirement": { "enchanting": 5 },
  "effects": [
    { "type": "cold_damage", "value": 12, "description": "+12 cold damage" },
    { "type": "slow", "value": 0.20, "duration": 3, "description": "20% slow for 3 seconds" }
  ],
  "materials": [
    { "item_id": "i-enchanting-dust", "qty": 20 },
    { "item_id": "i-magic-essence", "qty": 5 },
    { "item_id": "i-frost-crystal", "qty": 1 }
  ],
  "enchanting_time_seconds": 30,
  "success_rate": 0.85,
  "failure_effect": "material_loss",
  "removable": true,
  "removal_cost": { "item_id": "i-disenchant-scroll", "qty": 1 },
  "synergy": { "rune_type": "frost", "bonus_damage": 0.15 },
  "lore": "The blade frosts over as the enchantment takes hold. Cold radiates from the steel."
}
```

### Armor Enchantments

**Example — Armor Enchantment:**
```json
{
  "enchantment_id": "ench-iron-skin",
  "name": "Iron Skin",
  "type": "armor",
  "tier": "lesser",
  "level_requirement": 5,
  "skill_requirement": { "enchanting": 3 },
  "effects": [
    { "type": "defense_bonus", "value": 5, "description": "+5 defense" },
    { "type": "damage_reduction", "value": 0.05, "description": "5% damage reduction" }
  ],
  "materials": [
    { "item_id": "i-enchanting-dust", "qty": 10 },
    { "item_id": "i-magic-essence", "qty": 2 }
  ],
  "enchanting_time_seconds": 20,
  "success_rate": 0.90,
  "failure_effect": "stat_reduction",
  "removable": true,
  "removal_cost": { "item_id": "i-disenchant-scroll", "qty": 1 },
  "synergy": { "rune_type": "iron", "bonus_defense": 3 },
  "lore": "Your skin hardens like tempered steel. Blades glance off harmlessly."
}
```

### Unique Enchantments (Found Only)

**Example — Legendary Enchantment:**
```json
{
  "enchantment_id": "ench-undying-flame",
  "name": "Undying Flame",
  "type": "weapon",
  "tier": "legendary",
  "level_requirement": 20,
  "skill_requirement": { "enchanting": 15 },
  "effects": [
    { "type": "fire_damage", "value": 30, "description": "+30 fire damage" },
    { "type": "ignite", "value": 0.25, "duration": 5, "description": "25% chance to ignite for 5 seconds" },
    { "type": "life_on_kill", "value": 10, "description": "Heal 10 HP on kill" }
  ],
  "materials": [],
  "enchanting_time_seconds": 0,
  "success_rate": 1.0,
  "removable": false,
  "unique": true,
  "lore": "Only one blade in the realm bears this enchantment. It burns with the fire of a dying star."
}
```

## Enchantment Slot Rules
- Weapons: max 2 enchantment slots (3 for legendary tier)
- Armor: max 1 enchantment slot per piece
- Enchantments occupy a slot permanently (removable via disenchant)
- Higher tier enchantments require higher enchanting skill
- Failed enchantment may destroy materials or reduce item stats
- Enchantments can be stacked with runes (synergy bonuses apply)

---

# Level Scaling

Both players and weapons scale with levels. XP is gained through combat, crafting, exploration, and quests.

## XP Requirements by Level

| Level | XP to Next | Total XP | Stat Points | Skill Points |
|-------|------------|----------|-------------|--------------|
| 1 | 100 | 0 | 0 | 0 |
| 2 | 250 | 100 | 2 | 1 |
| 3 | 500 | 350 | 2 | 1 |
| 5 | 1000 | 1350 | 3 | 2 |
| 10 | 3000 | 8500 | 5 | 3 |
| 15 | 6000 | 32000 | 5 | 3 |
| 20 | 10000 | 87000 | 5 | 3 |

## Weapon Level Scaling

| Weapon Level | Damage Multiplier | Durability Bonus | Unlock |
|--------------|-------------------|------------------|--------|
| 1 | 1.0x | +0 | Base stats |
| 3 | 1.1x | +10 | Upgrade Path 1 |
| 5 | 1.2x | +25 | Upgrade Path 2 |
| 8 | 1.35x | +50 | Upgrade Path 3 |
| 10 | 1.5x | +75 | Rune Slot +1 |
| 15 | 1.75x | +120 | Enchantment Slot +1 |
| 20 | 2.0x | +200 | Masterwork Chance +20% |

## XP Sources

| Activity | XP Gained | Notes |
|----------|-----------|-------|
| Kill Monster | 10-500 | Scales with monster level |
| Complete Quest | 50-2000 | Quest difficulty determines amount |
| Craft Item | 5-100 | Higher quality = more XP |
| Discover Biome | 200 | First-time discovery only |
| Mine Ore | 10-30 | Rarer ores = more XP |
| Enchant Item | 25-200 | Higher tier enchantment = more XP |
| Explore Chunk | 5 | First-time visit only |
| Defeat Boss | 500-5000 | Boss level determines amount |

---

# Buildings System

Buildings are **chunk-based structures** that bypass normal block rendering:
- A house = 2×2 chunks. Instead of loading 2×2 chunks of individual blocks, the entire house is loaded as a single structure.
- **When outside:** only the house exterior/stub is shown.
- **When entering:** chunks switch scope — only the interior blocks are loaded.

**Examples:**
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

**Example — Fire Giant (Volcano Boss):**
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

**Example:**
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

**Example:**
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

**Example:**
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

**Example — Boss:**
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

**Special Character JSON:**
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

---

# Biome System

Each biome has unique environmental conditions, monsters, resources, and hazards.

| Biome | Temperature | Wetness | Unique Resources | Unique Monsters | Hazards |
|-------|-------------|---------|------------------|-----------------|---------|
| **Plain** | 20-35°C | 30-50 | Wheat, wild herbs, clay | Wolves, bandits | None |
| **Volcano** | 80-200°C | 0-10 | Obsidian, sulfur, fire crystals | Fire Giants, lava slugs, ember bats | Lava pools, toxic fumes, heat damage |
| **Snow Forest** | -20-5°C | 40-70 | Ice crystals, frostwood, fur | Yetis, ice wraiths, frost spiders | Frostbite, blizzards, hypothermia |
| **Deepslate** | 5-15°C | 60-90 | Darkstone, crystal veins, rare ores | Cave Crawlers, shadow stalkers, mimics | Cave-ins, darkness, poisonous gas |
| **Savana** | 30-50°C | 5-20 | Cactus fruit, sunstone, dry wood | Scorpions, sand worms, hyenas | Quicksand, dehydration, sandstorms |

**Example — Biome Transition:**
```python
# Gradual biome transition over 3-5 chunks
# Plain → Savana:
#   Chunk 0: plain (temp=25, wetness=40)
#   Chunk 1: plain_savana_border (temp=30, wetness=30)
#   Chunk 2: savana (temp=38, wetness=15)
```

---

# Chemical & Physics Interactions

Blocks and items interact based on their physics properties.

**Examples:**
```json
{
  "interaction_id": "chem-water-fire",
  "type": "chemical",
  "trigger": "water_contacts_fire",
  "result": "steam_cloud",
  "effect": { "visibility_reduction": 0.8, "fire_damage_reduction": 0.5 },
  "lore": "Water meets flame — steam rises, obscuring all."
}
```

```json
{
  "interaction_id": "chem-poison-fire",
  "type": "chemical",
  "trigger": "poison_contacts_fire",
  "result": "toxic_fumes",
  "effect": { "damage_per_sec": 5, "radius": 3 },
  "lore": "Burning venom releases its essence into the air."
}
```

```json
{
  "interaction_id": "physics-electricity-water",
  "type": "physics",
  "trigger": "electricity_source_near_water",
  "result": "electrified_pool",
  "effect": { "damage_on_contact": 15, "stun_chance": 0.3 },
  "lore": "The water crackles with unnatural energy. Step carefully."
}
```

---

# Weather System

Dynamic weather affects gameplay, visibility, and entity behavior.

| Weather | Effect | Biome Affected |
|---------|--------|----------------|
| **Clear** | No modifiers | All |
| **Rain** | +50% wetness, fire damage -20%, mud slows movement | Plain, Savana |
| **Blizzard** | -30% visibility, frostbite damage, ice forms on water | Snow Forest |
| **Ashfall** | -20% visibility, fire damage +10%, lava pools expand | Volcano |
| **Fog** | -60% visibility, entity detection range reduced | Deepslate, Plain |
| **Sandstorm** | -50% visibility, dehydration accelerated, wind damage | Savana |

**Example — Weather State:**
```json
{
  "weather_id": "w-volcano-ashfall",
  "type": "ashfall",
  "intensity": 0.7,
  "duration_minutes": 45,
  "effects": {
    "visibility_reduction": 0.2,
    "fire_damage_modifier": 1.1,
    "lava_pool_expansion": 0.1,
    "entity_behavior_change": { "fire_monsters": "aggressive", "others": "cautious" }
  },
  "lore": "The volcano breathes. Ash falls like black snow, coating everything in a gritty shroud."
}
```
