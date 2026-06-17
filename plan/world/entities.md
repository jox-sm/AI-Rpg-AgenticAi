# Entity System

## Overview
Entities include all living creatures, undead, constructs, and NPCs. Each has unique AI behaviors, stats, and interactions with the world.

## Entity Types

### Humanoid
| Type | HP | Damage | Special | Behavior |
|------|-----|--------|---------|----------|
| Goblin | 20 | 1d6 | Pack tactics | Aggressive |
| Orc | 40 | 2d6 | Rage, Intimidation | Aggressive |
| Elf | 30 | 1d6 | Magic, Stealth | Defensive |
| Dwarf | 45 | 2d6 | Tough, Craft | Defensive |
| Human | 35 | 1d8 | Versatile | Variable |
| Troll | 60 | 2d8 | Regeneration | Aggressive |
| Ogre | 80 | 3d6 | Smash, Throw | Aggressive |
| Vampire | 50 | 1d8+drain | Life steal, Transform | Cunning |
| Werewolf | 70 | 2d6+bleed | Transform, Scent | Aggressive |
| Lich | 100 | 2d8+magic | Undead, Spells | Cunning |

### Beasts
| Type | HP | Damage | Special | Behavior |
|------|-----|--------|---------|----------|
| Wolf | 25 | 1d6+bleed | Pack, Howl | Pack |
| Bear | 50 | 2d6 | Maul, Intimidation | Territorial |
| Spider | 20 | 1d4+poison | Web, Climb | Ambush |
| Snake | 15 | 1d4+poison | Stealth, Bite | Ambush |
| Eagle | 20 | 1d4 | Fly, Spot | Scavenger |
| Shark | 40 | 2d6 | Swim, Blood sense | Aggressive |
| Dragon | 150 | 4d6+breath | Fly, Hoard, Element | Cunning |
| Phoenix | 100 | 3d6+fire | Rebirth, Flight | Solitary |
| Griffin | 80 | 3d6 | Fly, Dive | Territorial |
| Wyvern | 120 | 3d6+poison | Fly, Venom | Aggressive |

### Undead
| Type | HP | Damage | Special | Behavior |
|------|-----|--------|---------|----------|
| Zombie | 15 | 1d4 | Slow, Immune pain | Mindless |
| Skeleton | 10 | 1d6 | Ranged, Tactics | Tactical |
| Ghost | 25 | 1d6+drain | Phase, Drain | Cunning |
| Wraith | 40 | 2d6+drain | Life steal, Shadow | Cunning |
| Mummy | 60 | 2d6 | Curse, Resists | Territorial |
| Vampire Lord | 100 | 2d8+drain | Transform, Dominate | Cunning |
| Lich King | 200 | 3d8+magic | Undead army, Spells | Cunning |
| Bone Dragon | 150 | 4d6 | Flying, Fear aura | Territorial |
| Death Knight | 120 | 3d6+holy | Death grip, Unholy | Aggressive |
| Specter | 30 | 1d6+drain | Phase, Drain | Ambush |

### Constructs
| Type | HP | Damage | Special | Behavior |
|------|-----|--------|---------|----------|
| Golem | 100 | 3d6 | Slow, Tough | Territorial |
| Iron Golem | 150 | 4d6 | Resists magic | Territorial |
| Crystal Golem | 80 | 2d8 | Reflects spells | Territorial |
| Clockwork | 40 | 1d8 | Fast, Precise | Tactical |
| Automaton | 60 | 2d6 | Ranged, Shield | Tactical |
| Warforged | 90 | 3d6 | Magic immune | Aggressive |
| Guardian | 200 | 4d8 | Boss, Phases | Territorial |
| Sentinel | 120 | 3d8 | AoE attacks | Territorial |
| Colossus | 300 | 6d6 | Massive, Slow | Territorial |
| Dragon Construct | 250 | 5d6+breath | Flying, Magic | Cunning |

### Elementals
| Type | HP | Damage | Special | Behavior |
|------|-----|--------|---------|----------|
| Fire Elemental | 60 | 2d6+fire | Burn, Immune fire | Aggressive |
| Water Elemental | 70 | 2d8 | Push, Heal | Defensive |
| Earth Elemental | 90 | 3d6 | Armor, Slam | Territorial |
| Air Elemental | 50 | 2d6 | Push, Flight | Aggressive |
| Lightning Elemental | 55 | 2d8+shock | Chain, Stun | Aggressive |
| Ice Elemental | 65 | 2d6+cold | Freeze, Slow | Defensive |
| Magma Elemental | 80 | 3d6+fire | Lava, Burn | Aggressive |
| Storm Elemental | 75 | 2d8+lightning | AoE, Stun | Aggressive |
| Crystal Elemental | 85 | 2d8 | Reflect, Beam | Territorial |
| Shadow Elemental | 60 | 2d6+shadow | Phase, Fear | Cunning |

### Demons
| Type | HP | Damage | Special | Behavior |
|------|-----|--------|---------|----------|
| Imp | 20 | 1d4+fire | Teleport, Stealth | Cunning |
| Hellhound | 40 | 2d6+fire | Pack, Breath | Aggressive |
| Fiend | 60 | 2d8+fire | Fear aura, Dominate | Cunning |
| Balrog | 150 | 4d6+fire | Whip, Fear | Aggressive |
| Pit Fiend | 200 | 5d6+fire | AoE, Teleport | Cunning |
| Demon Lord | 300 | 6d8+fire | Summons, Magic | Cunning |
| Succubus | 50 | 1d6+charm | Charm, Seduce | Cunning |
| Incubus | 50 | 1d6+drain | Life steal, Charm | Cunning |
| Marilith | 80 | 2d6 | Multi-attack, Poison | Aggressive |
| Glabrezu | 100 | 3d6 | Anti-magic, Fear | Cunning |

### Fey
| Type | HP | Damage | Special | Behavior |
|------|-----|--------|---------|----------|
| Pixie | 15 | 1d4 | Fly, Illusion | Trickster |
| Sprite | 20 | 1d4+electric | Electric, Fly | Aggressive |
| Satyr | 35 | 1d6 | Music, Charm | Friendly |
| Dryad | 40 | 1d6+poison | Entangle, Nature | Defensive |
| Treant | 100 | 2d8 | Slow, Tough | Territorial |
| Unicorn | 60 | 2d6+holy | Heal, Purify | Friendly |
| Pegasus | 50 | 2d6 | Fly, Charge | Friendly |
| Phoenix | 100 | 3d6+fire | Rebirth | Solitary |
| Dragon (Fey) | 120 | 3d6+magic | Shapeshift | Cunning |
| Archfey | 150 | 4d6+charm | Illusion, Dominate | Trickster |

### Giants
| Type | HP | Damage | Special | Behavior |
|------|-----|--------|---------|----------|
| Hill Giant | 100 | 3d8 | Throw, Intimidate | Aggressive |
| Frost Giant | 120 | 3d8+cold | Freeze, Blizzard | Territorial |
| Fire Giant | 130 | 3d8+fire | Forge, Fire breath | Territorial |
| Stone Giant | 150 | 4d8 | Throw boulders | Territorial |
| Cloud Giant | 110 | 3d8 | Flight, Lightning | Cunning |
| Storm Giant | 140 | 4d8+lightning | Weather control | Cunning |
| Elder Giant | 200 | 5d8 | Earthquake, Immune | Territorial |
| Titan | 300 | 6d8 | AoE, Magic | Cunning |
| Jotunn | 250 | 5d8+cold | Blizzard, Freeze | Aggressive |
| Primordial | 400 | 8d8 | Reality warp | Cunning |

## AI Behavior System

### Need-Based AI
Each entity has needs that drive behavior:
- **Hunger**: Seeks food, hunts
- **Safety**: Flees when threatened
- **Social**: Seeks company, forms groups
- **Territory**: Defends home area
- **Reproduction**: Seeks mates
- **Curiosity**: Investigates new things

### Behavior Trees
```
Root
├─ Survival
│  ├─ Flee if HP < 20%
│  ├─ Heal if possible
│  └─ Find safe spot
├─ Combat
│  ├─ Engage if strong enough
│  ├─ Use special abilities
│  ├─ Target weaknesses
│  └─ Retreat if losing
├─ Social
│  ├─ Call for help
│  ├─ Coordinate with allies
│  └─ Intimidate enemies
└─ Exploration
   ├─ Scout area
   ├─ Find resources
   └─ Report findings
```

### Combat Intelligence
| Type | Strategy |
|------|----------|
| Aggressive | Charge, focus weakest |
| Defensive | Protect allies, use shields |
| Tactical | Target weaknesses, flank |
| Retreat | Flee when low HP |
| Support | Heal/buff allies |
| Ambush | Hide, surprise attack |
| Pack | Coordinate attacks |
| Territorial | Defend area |

### Pack Tactics
- **Wolves**: Surround and flank
- **Goblins**: Bait and ambush
- **Skeletons**: Formation fighting
- **Demons**: Hit and run
- **Undead**: Overwhelm with numbers

### Adaptation
- Learn from player tactics
- Change strategies mid-fight
- Use environment advantages
- Counter player abilities

## NPC Systems

### NPC Types
| Type | Function | Interaction |
|------|----------|-------------|
| Merchant | Buy/sell items | Barter, Haggling |
| Quest Giver | Provide quests | Dialogue, Rewards |
| Trainer | Teach skills | Training, Cost |
| Blacksmith | Repair/craft | Crafting, Upgrades |
| Healer | Heal/cure | Services, Cost |
| Guard | Patrol, protect | Law, Combat |
| Innkeeper | Rest, info | Lodging, Rumors |
| Farmer | Provide food | Trade, Tasks |
| Miner | Provide ore | Trade, Tasks |
| Enchanter | Enchant items | Services, Cost |

### Relationship System
- **Friendship**: 0-100 scale
- **Romance**: Special dialogue options
- **Rivalry**: Compete for resources
- **Enemy**: Hostile interactions
- **Indifferent**: Neutral

### Faction System
| Faction | Values | Enemies | Allies |
|---------|--------|---------|--------|
| Merchants Guild | Trade, Profit | Thieves | Artisans |
| Mages Circle | Magic, Knowledge | Anti-magic | Scholars |
| Knights Order | Honor, Duty | Undead | Church |
| Thieves Guild | Stealth, Freedom | Guards | Rogues |
| Church | Faith, Healing | Demons | Paladins |
| Assassins | Contracts, Silence | Everyone | None |
| Rangers | Nature, Protection | Logging | Druids |
| Dwarven Clan | Craft, Tradition | Goblins | Elves |
| Elven Court | Magic, Nature | Orcs | Dwarves |
| Undead Legion | Death, Power | Living | Demons |

### NPC Memory
- Remember player actions
- React to past decisions
- Spread rumors
- Hold grudges
- Show gratitude

### NPC Schedules
- Day/night routines
- Weekly activities
- Seasonal events
- Special occasions

## Entity Progression

### Level Scaling
| Level | HP Bonus | Damage Bonus | Special |
|-------|----------|--------------|---------|
| 1-10 | +5/level | +1/level | Basic abilities |
| 11-20 | +8/level | +2/level | Advanced abilities |
| 21-30 | +12/level | +3/level | Elite abilities |
| 31-40 | +15/level | +4/level | Champion abilities |
| 41-50 | +20/level | +5/level | Legendary abilities |
| 51-60 | +25/level | +6/level | Mythic abilities |

### Elite/Champion/Legendary
- **Elite**: +50% stats, special abilities
- **Champion**: +100% stats, unique mechanics
- **Legendary**: +200% stats, boss mechanics

### Boss Mechanics
- Multiple phases
- Enrage timers
- Special attacks
- Weaknesses
- Summons

## Entity Spawning

### Spawn Conditions
- **Biome**: Specific creatures per biome
- **Time**: Day/night cycles
- **Weather**: Weather-dependent spawns
- **Level**: Area-appropriate levels
- **Population**: Max entities per area

### Spawn Rates
| Rate | Description |
|------|-------------|
| Common | Every few minutes |
| Uncommon | Every 30 minutes |
| Rare | Every 2 hours |
| Very Rare | Every 8 hours |
| Legendary | Every 24 hours |

### Spawn Mechanics
- **Natural Spawning**: Based on conditions
- **Event Spawning**: Triggered by events
- **Quest Spawning**: For missions
- **Boss Spawning**: Rare, announced

---

This entity system provides diverse creatures with intelligent AI and deep interactions.
