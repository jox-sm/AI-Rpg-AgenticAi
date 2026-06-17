# Progression System

## Overview

Character progression features deep skill trees, prestige classes, and multiple advancement paths. Players gain power through levels, skills, equipment, and special abilities.

## Core Stats

### Primary Stats

| Stat | Effect | Cap |
|------|--------|-----|
| Strength (STR) | Physical damage, carry weight | 100 |
| Dexterity (DEX) | Accuracy, speed, dodge | 100 |
| Constitution (CON) | HP, stamina, resistances | 100 |
| Intelligence (INT) | Magic damage, mana, skills | 100 |
| Wisdom (WIS) | Perception, willpower, magic resist | 100 |
| Charisma (CHA) | Persuasion, leadership, NPC reactions | 100 |
| Luck (LUC) | Critical chance, loot quality, events | 100 |

### Secondary Stats

| Stat | Formula | Effect |
|------|---------|--------|
| HP | `(CON * 2) + (Level * 5)` | Health points |
| MP | `(INT * 2) + (Level * 3)` | Mana points |
| Stamina | `(CON + DEX) + (Level * 2)` | Action points |
| Speed | `DEX + (Level * 0.5)` | Turn order |
| Defense | `Armor + (CON * 0.5)` | Damage reduction |
| Magic Resist | `WIS + (INT * 0.5)` | Spell resistance |
| Critical | `(DEX * 0.2) + (LUC * 0.3)` | Crit chance % |
| Dodge | `(DEX * 0.3) + (LUC * 0.2)` | Dodge chance % |

### Stat Growth

- Base stats: 10 at level 1
- Primary stat gain: +3 per level (distributed)
- Secondary stats: Calculated from primary

## Level System

### Level Cap

- Base level cap: 50
- Prestige levels: +10 per prestige (max 5 prestiges)
- Total possible level: 100

### Experience Table

| Level Range | XP Per Level | Total XP (Cumulative) |
|-------------|--------------|----------------------|
| 1-10 | 100 * level | 5,500 |
| 11-20 | 200 * level | 33,000 |
| 21-30 | 400 * level | 126,000 |
| 31-40 | 800 * level | 484,000 |
| 41-50 | 1,600 * level | 1,924,000 |

### XP Sources

| Source | XP Amount |
|--------|-----------|
| Enemy Kill | Enemy level * 10 |
| Quest Completion | Quest level * 50 |
| Discovery | 10-100 per discovery |
| Crafting | Item level * 5 |
| Gathering | 5 per resource |
| Trading | 1 per transaction |
| Exploration | 10 per new area |

### Milestone Levels

| Level | Milestone | Reward |
|-------|-----------|--------|
| 10 | Class Selection | Unlock class |
| 20 | Advanced Class | Class upgrade |
| 30 | Prestige Unlock | Prestige available |
| 40 | Legendary Class | Legendary abilities |
| 50 | Master Class | Master abilities |

## Skill System

### Skill Categories

| Category | Skills | Focus |
|----------|--------|-------|
| Combat | 20 | Weapon mastery |
| Magic | 15 | Spell casting |
| Stealth | 10 | Subtlety |
| Survival | 10 | Nature |
| Crafting | 10 | Creation |
| Social | 10 | Interaction |

### Combat Skills

| Skill | Effect | Cap |
|-------|--------|-----|
| Swordsmanship | Sword damage, techniques | 100 |
| Archery | Bow damage, accuracy | 100 |
| Heavy Weapons | Axe/Mace damage, armor pen | 100 |
| Polearms | Spear damage, reach | 100 |
| Dual Wielding | Two-weapon fighting | 100 |
| Shield Mastery | Block chance, bash damage | 100 |
| Critical Strike | Crit chance, crit damage | 100 |
| Armor Penetration | Ignore armor % | 100 |
| Weapon Finesse | Dex-based damage | 100 |
| Two-Handed | Two-handed weapon bonus | 100 |

### Magic Skills

| Skill | Effect | Cap |
|-------|--------|-----|
| Fire Magic | Fire spells, damage | 100 |
| Water Magic | Water spells, healing | 100 |
| Earth Magic | Earth spells, defense | 100 |
| Air Magic | Air spells, speed | 100 |
| Lightning Magic | Lightning spells, stun | 100 |
| Ice Magic | Ice spells, freeze | 100 |
| Poison Magic | Poison spells, DoT | 100 |
| Holy Magic | Holy spells, undead bonus | 100 |
| Shadow Magic | Shadow spells, drain | 100 |
| Runic Magic | Runic spells, utility | 100 |

### Stealth Skills

| Skill | Effect | Cap |
|-------|--------|-----|
| Stealth | Invisibility, sneak | 100 |
| Lockpicking | Open locks | 100 |
| Trap Disarm | Disable traps | 100 |
| Pickpocket | Steal items | 100 |
| Backstab | Extra damage from stealth | 100 |
| Poison Craft | Apply poisons | 100 |
| Shadow Step | Teleport short distance | 100 |
| Assassinate | Instant kill chance | 100 |
| Evasion | Dodge multiple attacks | 100 |
| Vanish | Escape combat | 100 |

### Survival Skills

| Skill | Effect | Cap |
|-------|--------|-----|
| Herbalism | Gather herbs, identify | 100 |
| Tracking | Find creatures, tracks | 100 |
| Hunting | Kill animals, skinning | 100 |
| Fishing | Catch fish | 100 |
| Cooking | Prepare food, buffs | 100 |
| Camping | Set camp, rest safely | 100 |
| Cartography | Create maps | 100 |
| Mining | Gather ores | 100 |
| Lumberjacking | Gather wood | 100 |
| Stonemasonry | Gather stones | 100 |

### Crafting Skills

| Skill | Effect | Cap |
|-------|--------|-----|
| Smithing | Forge weapons/armor | 100 |
| Leatherworking | Create leather items | 100 |
| Tailoring | Create cloth items | 100 |
| Alchemy | Brew potions | 100 |
| Enchanting | Enchant items | 100 |
| Runeforging | Create runes | 100 |
| Jewelry | Create accessories | 100 |
| Woodworking | Create bows/staves | 100 |
| Gemcutting | Cut gems | 100 |
| Transmutation | Convert materials | 100 |

### Social Skills

| Skill | Effect | Cap |
|-------|--------|-----|
| Persuasion | Convince NPCs | 100 |
| Intimidation | Threaten NPCs | 100 |
| Bartering | Better prices | 100 |
| Leadership | Party bonuses | 100 |
| Performance | Entertain, distract | 100 |
| Deception | Lie, disguise | 100 |
| Insight | Read NPCs | 100 |
| Streetwise | Urban knowledge | 100 |
| Etiquette | Noble interaction | 100 |
| Gossip | Gather information | 100 |

### Skill Progression

- Use skill to gain XP
- XP thresholds for ranks
- Ranks: Novice, Apprentice, Journeyman, Expert, Master, Grandmaster
- Each rank unlocks new abilities

## Class System

### Base Classes

| Class | Primary Stats | Role |
|-------|---------------|------|
| Warrior | STR, CON | Tank/DPS |
| Rogue | DEX, LUC | DPS/Stealth |
| Mage | INT, WIS | Magic DPS |
| Ranger | DEX, WIS | Ranged DPS |
| Cleric | WIS, CHA | Healer/Support |
| Paladin | STR, CHA | Tank/Healer |
| Necromancer | INT, WIS | Magic DPS/Summoner |
| Bard | CHA, DEX | Support/Debuffer |
| Monk | DEX, CON | Melee DPS |
| Artificer | INT, DEX | Ranged DPS/Crafter |

### Advanced Classes (Level 20)

| Class | Base Class | Specialization |
|-------|------------|----------------|
| Berserker | Warrior | Rage, damage |
| Gladiator | Warrior | Arena combat |
| Assassin | Rogue | Single target |
| Thief | Rogue | Stealth, traps |
| Sorcerer | Mage | Elemental magic |
| Wizard | Mage | Arcane magic |
| Beastmaster | Ranger | Pet companion |
| Sniper | Ranger | Ranged precision |
| Priest | Cleric | Healing, buffs |
| Inquisitor | Cleric | Anti-undead |
| Avenger | Paladin | Holy damage |
| Crusader | Paladin | Tank, auras |
| Lich | Necromancer | Undead army |
| Blood Mage | Necromancer | Life drain |
| Skald | Bard | War songs |
| Minstrel | Bard | Social, buffs |
| Shaolin | Monk | Martial arts |
| Alchemist | Artificer | Transmutation |

### Prestige Classes (Level 30, 1 Prestige)

| Class | Requirements | Specialization |
|-------|--------------|----------------|
| Dragon Knight | Dragon kills | Dragon abilities |
| Archmage | Magic mastery | Ultimate spells |
| Shadow Lord | Stealth mastery | Shadow magic |
| Templar | Holy service | Holy warrior |
| Rune Master | Runic mastery | Rune magic |
| Blood Knight | Vampire kills | Blood magic |
| Elementalist | All elements | Elemental mastery |
| Chronomancer | Time magic | Time manipulation |
| Planar Walker | Dimensional travel | Dimensional magic |
| Godslayer | God kills | Divine power |

### Legendary Classes (Level 40, 2 Prestige)

| Class | Requirements | Specialization |
|-------|--------------|----------------|
| Dragon King | All dragons | Dragon form |
| Archlich | All undead | Undead army |
| Shadowmancer | Shadow mastery | Shadow realm |
| Celestial | Angel service | Divine form |
| Void Walker | Void magic | Dimensional |
| Elemental Lord | All elements | Elemental form |
| Chrono Lord | Time mastery | Time stop |
| Planar Lord | All planes | Reality warp |
| God Hand | All gods | Divine weapon |
| World Ender | Apocalypse | Ultimate power |

### Master Classes (Level 50, 3 Prestige)

| Class | Requirements | Specialization |
|-------|--------------|----------------|
| Eternal | All masteries | Immortal |
| Infinite | All skills 100 | Omniscient |
| Creator | All crafts | Master crafter |
| Destroyer | All combat | War master |
| Sage | All magic | Magic master |
| Shadow King | All stealth | Shadow master |
| Life Giver | All healing | Life master |
| Death Bringer | All death | Death master |
| Time Lord | All time | Time master |
| World Master | All world | Reality master |

## Ability System

### Ability Types

| Type | Effect | Cost |
|------|--------|------|
| Active | Used manually | Stamina/Mana |
| Passive | Always active | None |
| Toggle | On/off switch | Stamina |
| Channel | Channeled over time | Mana |
| Ultimate | Powerful, long cooldown | All resources |

### Ability Ranks

| Rank | Power | Unlock |
|------|-------|--------|
| Novice | Base | Class selection |
| Apprentice | +25% | Skill rank 25 |
| Journeyman | +50% | Skill rank 50 |
| Expert | +75% | Skill rank 75 |
| Master | +100% | Skill rank 100 |
| Grandmaster | +150% | Prestige |

### Ability Cooldowns

| Type | Cooldown |
|------|----------|
| Basic | 0-5 seconds |
| Moderate | 10-30 seconds |
| Advanced | 30-60 seconds |
| Ultimate | 60-120 seconds |
| Legendary | 120-300 seconds |

## Talent Tree System

### Tree Structure

Each class has 3 talent trees with 5 tiers:

- **Tier 1:** 3 talents (choose 1)
- **Tier 2:** 3 talents (choose 1)
- **Tier 3:** 3 talents (choose 1)
- **Tier 4:** 3 talents (choose 1)
- **Tier 5:** Ultimate talent (choose 1)

### Talent Points

- Gain 1 talent point per level
- Total: 50 talent points at max level
- Can respec at NPC for gold

### Example Talent Trees (Warrior)

#### Protection Tree

- **Tier 1:** Shield Wall, Toughness, Iron Skin
- **Tier 2:** Shield Slam, Last Stand, Improved Block
- **Tier 3:** Spell Reflect, Devastate, Heroic Strike
- **Tier 4:** Shield Mastery, Taunt, Shield Charge
- **Tier 5:** Avatar (Ultimate)

#### Arms Tree

- **Tier 1:** Improved Strike, Cruelty, Weapon Mastery
- **Tier 2:** Mortal Strike, Cleave, Overpower
- **Tier 3:** Unbridled Wrath, Sweep Strikes, Improved Whirlwind
- **Tier 4:** Improved Mortal Strike, Bloodthirst, Slam
- **Tier 5:** Bladestorm (Ultimate)

#### Fury Tree

- **Tier 1:** Dual Wield Specialization, Improved Battle Shout, Enrage
- **Tier 2:** Improved Execute, Bloodlust, Improved Berserker Rage
- **Tier 3:** Improved Whirlwind, Flurry, Intimidating Shout
- **Tier 4:** Improved Slam, Berserker Rage, Improved Execute
- **Tier 5:** Titan's Grip (Ultimate)

## Prestige System

### Prestige Mechanics

- Reach level 50 to prestige
- Reset to level 1 with bonuses
- **Keep:** Skills, talents, gold, items
- **Lose:** Level, stat points, talent points

### Prestige Benefits

| Prestige | Bonus | Unlock |
|----------|-------|--------|
| 1 | +10% all stats | Prestige class |
| 2 | +20% all stats | Legendary class |
| 3 | +30% all stats | Master class |
| 4 | +40% all stats | Ultimate abilities |
| 5 | +50% all stats | Max prestige |

### Prestige Perks

Each prestige grants a unique perk:

- **Prestige 1:** Second Wind (HP regen)
- **Prestige 2:** Magic Find (better loot)
- **Prestige 3:** Experience Bonus (+50% XP)
- **Prestige 4:** Gold Bonus (+100% gold)
- **Prestige 5:** Godslayer (damage to gods)

## Equipment Progression

### Item Levels

| Level Range | Item Quality | Stats |
|-------------|--------------|-------|
| 1-10 | Common | Basic |
| 11-20 | Uncommon | Improved |
| 21-30 | Rare | Good |
| 31-40 | Epic | Great |
| 41-50 | Legendary | Amazing |
| 51-60 | Mythic | Ultimate |

### Item Scaling

- Items scale with player level
- Higher level = better stats
- Affixes improve with level
- Enchantments scale with skill

### Set Items

Wearing multiple pieces of a set grants bonuses:

| Pieces | Bonus |
|--------|-------|
| 2 | Minor bonus |
| 3 | Medium bonus |
| 4 | Major bonus |
| 5 | Set bonus |
| 6 | Ultimate bonus |

## Progression Milestones

### Early Game (1-10)

- Learn basic mechanics
- Choose class
- Acquire starting gear
- Complete tutorial area

### Mid Game (11-30)

- Specialize class
- Acquire rare gear
- Master combat
- Explore world

### Late Game (31-50)

- Prestige available
- Acquire epic gear
- Master skills
- Defeat bosses

### End Game (50+)

- Multiple prestiges
- Acquire legendary gear
- Master all skills
- Ultimate challenges

## Progression Formulas

### Damage Formula

```
Base Damage = Weapon Damage + (STR * 0.5)
Modifier = 1 + (Skill Level * 0.01) + (Ability Bonus)
Final Damage = Base Damage * Modifier * (1 + Crit Bonus)
```

### HP Formula

```
HP = (CON * 2) + (Level * 5) + (Gear Bonus)
```

### MP Formula

```
MP = (INT * 2) + (Level * 3) + (Gear Bonus)
```

### XP Formula

```
XP Required = Level * 100 * (1 + (Level * 0.1))
```

### Skill XP Formula

```
Skill XP = Action XP * (1 + (Related Stat * 0.01))
```

## Special Progression Systems

### Bloodline System

- Inherited abilities from ancestors
- Unlock through story progression
- Passive bonuses
- Active abilities

### Soul Binding

- Bind soul to item/stat
- Permanent choice
- Powerful bonuses
- Cannot be undone

### Curse Progression

- Curses evolve into powers
- Risk/reward mechanic
- Dark path progression
- Ultimate abilities

### Dream System

- Sleep grants visions
- Learn abilities through dreams
- Alternate progression
- Secret content

### Fate System

- Destiny points
- Fated encounters
- Prophecy fulfillment
- Special rewards

### Legacy System

- Dead characters leave bonuses
- New characters inherit
- Permanent world changes
- Long-term progression

---

*This progression system provides deep character development with multiple advancement paths and meaningful choices.*
