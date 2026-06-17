# World System

## Overview

The world uses diamond-shaped chunk rendering with dynamic biomes, weather, and environmental interactions. Each chunk contains blocks with full physics simulation, creating a living, reactive environment that responds to player actions and natural forces.

---

## World Structure

### Chunk System

| Property | Value |
|----------|-------|
| Shape | Diamond |
| Size | 16x16 blocks per chunk |
| Render Radius | 4 chunks in each direction |
| Loading | Dynamic based on player position |
| Unloading | Automatic when outside render radius |

### Block Properties

Every block in the world has the following properties:

| Property | Range | Description |
|----------|-------|-------------|
| Material | Enum | Stone, dirt, wood, metal, etc. |
| Temperature | -100 to 200 | Affects mechanics and interactions |
| Wetness | 0-100 | Dampness level of the block |
| Fire Resistance | 0-100 | Resistance to fire damage |
| Electric Resistance | 0-100 | Resistance to electrical damage |
| Air Resistance | 0-100 | Resistance to wind/air forces |
| Shock Resistance | 0-100 | Resistance to shock damage |
| State | Enum | Solid, liquid, or gas |

### Block Types

| Block | Temperature | Wetness | Fire Resistance | Electric Resistance | Special Properties |
|-------|-------------|---------|-----------------|---------------------|-------------------|
| Stone | 20 | 0 | 80 | 60 | Fire/Electric resistant |
| Dirt | 20 | 20 | 20 | 10 | Grows plants |
| Grass | 20 | 30 | 10 | 10 | Flammable |
| Wood | 20 | 10 | 5 | 10 | Burns easily |
| Water | 15 | 100 | 0 | 90 | Conducts electricity |
| Lava | 200 | 0 | 100 | 0 | Burns, light source |
| Ice | -20 | 100 | 0 | 20 | Slides, melts |
| Sand | 25 | 5 | 10 | 5 | Shifts, buries |
| Metal | 20 | 0 | 30 | 100 | Conducts electricity |
| Crystal | 20 | 0 | 40 | 10 | Reflects light |
| Mushroom | 18 | 40 | 5 | 10 | Grows, releases spores |
| Bone | 20 | 0 | 10 | 5 | Undead attractant |

---

## Biome System

### Biome Types

| Biome | Temperature | Humidity | Enemies | Resources |
|-------|-------------|----------|---------|-----------|
| Forest | 20-30 | 40-60 | Wolves, Bears, Goblins | Wood, Herbs |
| Desert | 40-60 | 0-10 | Scorpions, Bandits, Sandworms | Sand, Gems |
| Tundra | -30 to -10 | 20-40 | Yetis, Ice Wolves, Frost Giants | Ice, Crystal |
| Swamp | 20-30 | 80-100 | Zombies, Frogs, Slimes | Poison, Herbs |
| Mountain | 0-20 | 20-40 | Gargoyles, Eagles, Dwarves | Metal, Gems |
| Ocean | 10-20 | 100 | Sharks, Mermaids, Krakens | Pearls, Coral |
| Volcano | 80-120 | 0-20 | Fire Elementals, Dragons | Obsidian, Magma |
| Crystal Caves | 15-25 | 10-30 | Crystal Golems, Bats | Crystals, Gems |
| Floating Islands | 15-25 | 30-50 | Harpies, Elementals | Clouds, Wind |
| Shadow Realm | 0-10 | 50-70 | Demons, Shadows, Undead | Soul Essence |

### Biome Transitions

Biomes do not have hard borders. Instead, transitions use fuzzy logic for smooth blending:

- **Mixed Blocks**: Transitional blocks appear at biome borders
- **Transitional Creatures**: Enemies from adjacent biomes may spawn
- **Mixed Resources**: Resources from both biomes available
- **Gradient Effects**: Temperature and humidity shift gradually

---

## Weather System

### Weather Types

| Weather | Effects | Duration |
|---------|---------|----------|
| Clear | Normal conditions | 1-3 days |
| Rain | -10% fire damage, +20% water effects, slippery terrain | 6-24 hours |
| Storm | -20% fire damage, +40% water effects, lightning strikes | 2-6 hours |
| Snow | -20% movement speed, -10% visibility | 1-3 days |
| Blizzard | -40% movement speed, -30% visibility | 6-12 hours |
| Fog | -30% visibility, stealth bonus | 4-8 hours |
| Wind | +10% air damage, -10% ranged accuracy | 2-6 hours |
| Heatwave | +20% fire damage, dehydration | 1-2 days |
| Eclipse | +50% shadow damage, -50% holy damage | 1-2 hours |
| Meteor Shower | Random damage across area, rare materials fall | 1-3 hours |

### Weather Effects

| Effect Category | Details |
|-----------------|---------|
| **Visibility** | Affects ranged attacks and stealth mechanics |
| **Movement** | Snow and rain slow movement; wind affects arrow trajectory |
| **Damage** | Elemental damage enhanced or reduced |
| **Spawning** | Different enemies appear in different weather |
| **Resources** | Special materials available only during rare weather |

---

## Physics System

### Temperature Effects

| Temperature Range | Effect |
|-------------------|--------|
| Below -20 | Frozen: -20% speed, ice damage taken |
| -20 to 0 | Cold: -10% speed |
| 0 to 40 | Normal: No effects |
| 40 to 80 | Hot: Dehydration, -10% stamina |
| Above 80 | Burning: Fire damage, melted items |

### Wetness Effects

| Wetness Level | Effect |
|---------------|--------|
| 0-20 (Dry) | Fire spreads easily |
| 20-40 (Damp) | Normal conditions |
| 40-60 (Wet) | -10% fire damage |
| 60-80 (Soaked) | -20% fire damage, conducts electricity |
| 80-100 (Drenched) | -30% fire damage, +50% electric damage |

### Core Mechanics

#### Fire Mechanics
- Spreads to adjacent flammable blocks
- Increases temperature of nearby blocks
- Can be extinguished by water
- Creates light source
- Smoke rises and spreads through air

#### Water Mechanics
- Flows downhill naturally
- Fills containers and low areas
- Conducts electricity
- Freezes in cold temperatures
- Evaporates in extreme heat

#### Electricity Mechanics
- Conducts through metal and water
- Jumps between conductors
- Stuns biological targets
- Ignores non-conductive materials

#### Air Mechanics
- Pushes lightweight objects
- Carries sound further
- Spreads fire and smoke
- Affects projectile trajectory

---

## Environmental Hazards

### Traps

| Trap | Damage | Effect | Detection |
|------|--------|--------|-----------|
| Pit | 2d6 | Fall damage | Perception |
| Spike | 1d6 + poison | Bleed, poison | Perception |
| Net | 0 | Restrained | Agility |
| Tripwire | 0 | Alert enemies | Perception |
| Poison Dart | 1d4 + poison | Poison | Perception |
| Fire Trap | 2d6 fire | Burns area | Perception |
| Lightning Trap | 2d8 electric | Stuns target | Perception |
| Frost Trap | 2d6 cold | Freezes target | Perception |
| Explosive | 3d6 | AoE damage | Perception |
| Teleport | 0 | Random location | Arcana |

### Environmental Damage

| Hazard | Damage per Turn |
|--------|-----------------|
| Lava | 10d10 fire |
| Acid | 5d10 acid |
| Vacuum | 1d6 |
| Extreme Cold | 2d6 cold |
| Extreme Heat | 2d6 fire |

### Natural Hazards

| Hazard | Effect |
|--------|--------|
| Collapsing Ceiling | 3d6 damage |
| Flood | Pushes and drowns |
| Sandstorm | 1d6 damage, blindness |
| Volcanic Eruption | 10d10 fire, lava flow |
| Aurora | Random magical effects |

---

## World Events

### Dynamic Events

| Event | Effect | Frequency |
|-------|--------|-----------|
| Earthquake | Terrain changes, reveals caves | Rare |
| Flood | Water level rises | Seasonal |
| Volcanic Eruption | New lava flows, rare materials | Rare |
| Meteor Shower | Craters form, rare materials | Very Rare |
| Eclipse | Shadow creatures appear | Rare |
| Auroras | Magical anomalies occur | Rare |
| Migration | Creature movements | Seasonal |
| War | Faction conflicts | Dynamic |

### Seasonal Changes

| Season | Effects |
|--------|---------|
| Spring | New growth, floods, mild temperatures |
| Summer | Hot, drought, increased insects |
| Autumn | Harvest, leaf fall, mild temperatures |
| Winter | Cold, snow, creature hibernation |

---

## Exploration

### Points of Interest

| Location | Description |
|----------|-------------|
| **Dungeons** | Multi-floor challenges with enemies and loot |
| **Ruins** | Lore discovery and puzzles |
| **Caves** | Resources and hidden dangers |
| **Towns** | Safety, shops, and NPCs |
| **Lairs** | Boss enemies with unique rewards |
| **Treasure Sites** | Rare loot deposits |
| **Shrines** | Buffs and quests |
| **Hidden Areas** | Secret content and easter eggs |

### Navigation

| Method | Description |
|--------|-------------|
| **Fog of War** | Explore to reveal map |
| **Cartography** | Create custom maps |
| **Landmarks** | Visual reference points |
| **Signposts** | Directional signs |
| **Compass** | Basic navigation |
| **Magic Map** | Reveals entire area |

### Travel

| Method | Speed | Requirements |
|--------|-------|--------------|
| Walking | Default | None |
| Running | Faster | Stamina cost |
| Swimming | Water areas | Swim skill |
| Climbing | Vertical surfaces | Climb skill |
| Boats | Water travel | Boat item |
| Mounts | Faster land travel | Mount item |
| Teleportation | Instant | Fast travel point discovered |

---

## World Generation

### Generation Algorithms

| Algorithm | Use Case |
|-----------|----------|
| **Perlin Noise** | Natural terrain generation |
| **Cellular Automata** | Cave systems |
| **Voronoi** | Biome region boundaries |
| **L-Systems** | Trees, plants, organic structures |
| **Wave Function Collapse** | Buildings, dungeons, structures |

### World Layers

| Layer | Depth | Contents |
|-------|-------|----------|
| 1. Surface | 0 | Grass, trees, water |
| 2. Underground | 1-50 | Caves, ores, dungeons |
| 3. Deep Underground | 51-100 | Rare ores, boss encounters |
| 4. Underworld | 101+ | Demons, endgame content |
| 5. Sky Islands | Above surface | Floating areas, unique biome |

---

## Summary

This world system provides a rich, dynamic environment with deep physics and environmental interactions. Key features include:

- **Diamond-shaped chunk rendering** for efficient world management
- **Full block physics** with temperature, wetness, and elemental properties
- **Ten distinct biomes** with smooth transitions
- **Dynamic weather** affecting gameplay mechanics
- **Realistic fire, water, electricity, and air** mechanics
- **Environmental hazards** including traps and natural disasters
- **Dynamic world events** and seasonal changes
- **Multiple travel methods** and exploration tools
- **Layered world generation** with five distinct depth levels
