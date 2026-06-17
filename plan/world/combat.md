# Combat Mechanics

## Overview
Combat in this text-based RPG is turn-based with real-time elements, featuring deep tactical decisions, elemental interactions, and environmental awareness.

---

## Core Systems

### Action Points (AP)
- Each turn grants AP based on speed stat
- Attacks cost 2-5 AP depending on weapon
- Spells cost 3-8 AP depending on power
- Movement costs 1 AP per tile
- Defensive actions cost 1 AP

### Stance System
Players choose a stance each turn:

| Stance | Effect | Bonus |
|--------|--------|-------|
| Aggressive | +30% damage, -20% defense | Critical hit chance +15% |
| Defensive | +30% defense, -20% damage | Counter-attack chance +20% |
| Balanced | No modifiers | Adaptability bonus |
| Stealth | +50% first hit damage | Must remain hidden |

### Combo Chain System
String attacks together for escalating bonuses:
- **2-hit combo**: +10% damage
- **3-hit combo**: +25% damage + stagger
- **4-hit combo**: +40% damage + bleed
- **5-hit combo**: +60% damage + special ability unlock

### Momentum System
Successive hits build momentum meter (0-100):

| Range | Effect |
|-------|--------|
| 0-30 | Normal |
| 31-60 | +15% damage, abilities cost less AP |
| 61-90 | +30% damage, special moves unlocked |
| 91-100 | Ultimate ability available, +50% damage |

---

## Damage Types

### Physical Damage
| Type | Strength | Effect |
|------|----------|--------|
| Blunt | Good against armor | Stuns |
| Slash | Good against flesh | Causes bleeding |
| Pierce | Ignores部分 armor | Targets vital spots |

### Elemental Damage
| Element | Primary Effect | Secondary Effect |
|---------|----------------|------------------|
| Fire | Damage over time | Spreads on dry surfaces |
| Water | Conducts electricity | Extinguishes fire |
| Earth | Armor piercing | Causes stun |
| Air | Pushes enemies | Interrupts spells |
| Lightning | Chain damage | Stuns mechanical enemies |
| Ice | Slows/freezes | Brittle condition |
| Poison | Damage over time | Stat debuffs |
| Holy | Extra damage to undead/demonic | Purification |
| Shadow | Ignores部分 defenses | Life steal |
| Runic | Magical damage | Bypasses resistances |

### Elemental Interactions
| Combination | Result |
|-------------|--------|
| Fire + Water | Steam (blind) |
| Fire + Earth | Magma (area damage) |
| Water + Lightning | Shock (chain stun) |
| Ice + Fire | Melt (reduced效果) |
| Air + Fire | Inferno (enhanced fire) |
| Earth + Air | Duststorm (blind + damage) |
| Shadow + Holy | Null (cancel effects) |

---

## Weapon System

### Weapon Types
| Type | Speed | Damage | Special |
|------|-------|--------|---------|
| Dagger | Fast | Low | Backstab bonus, poison |
| Sword | Medium | Medium | Balanced, parry |
| Axe | Slow | High | Armor break, cleave |
| Mace | Slow | High | Stun, shield break |
| Spear | Medium | Medium | Reach, dodge bonus |
| Bow | Medium | Medium | Range, volley |
| Crossbow | Slow | High | Armor pierce, slow reload |
| Staff | Medium | Low | Magic amplify, channel |
| Shield | Slow | Low | Block, bash, protection |

### Weapon Arts
Special abilities unique to weapon type:
- **Dance of Blades**: 5-hit combo with dagger
- **Shield Wall**: AoE defense boost
- **Earthquake Slam**: AoE stun with mace
- **Precision Shot**: Guaranteed critical with bow
- **Mana Surge**: Double spell power with staff

### Critical Hits
- **Base chance**: 5% + (Dexterity/10)
- **Critical multiplier**: 1.5x base damage

| Target Location | Damage Multiplier |
|-----------------|-------------------|
| Head | 2x |
| Heart | 2.5x |
| Limbs | 1.2x |

- **Critical effects**: Stagger, bleed, disarm

---

## Defense System

### Armor Types
| Armor | Defense | Weakness | Weight |
|-------|---------|----------|--------|
| Cloth | Low | Physical | Light |
| Leather | Medium | Fire | Light |
| Chain | Medium-High | Pierce | Medium |
| Plate | High | Lightning, Movement | Heavy |
| Robe | Low-Medium | Physical | Light |
| Crystal | Medium | Shatter | Medium |

### Evasion
- **Base**: 10% + (Agility/5)
- **Dodge**: Avoid all damage
- **Parry**: Deflect with weapon
- **Block**: Reduce damage with shield

### Counter-Attack System
- **Base chance**: 10% + (Perception/10)
- **Timing window**: 1 second after enemy attack
- **Successful counter**: Redirect damage
- **Perfect counter**: Double damage + stun

---

## Combat Positioning

### Flanking
| Position | Effect |
|----------|--------|
| Side attacks | +15% damage |
| Rear attacks | +30% damage + backstab |
| Surrounded | -20% defense for target |

### Height Advantage
| Position | Effect |
|----------|--------|
| Higher ground | +10% ranged damage |
| Lower ground | -10% ranged damage |
| Falling | 1d6 damage per 10 feet |

### Environmental Combat
| Terrain | Effect |
|---------|--------|
| Water | Slows movement, conducts electricity |
| Fire | Damage in area, spreads |
| Ice | Slips, prone condition |
| Smoke | Ranged attacks -20% |
| Darkness | All attacks -15%, stealth bonus |

---

## Status Effects

### Negative Status Effects
| Effect | Duration | Impact |
|--------|----------|--------|
| Bleed | 3 turns | 1d4 damage/turn |
| Poison | 5 turns | 1d6 damage/turn, -2 STR |
| Stun | 1 turn | Skip turn |
| Freeze | 2 turns | Skip turn, +50% damage |
| Blind | 3 turns | -50% accuracy |
| Silence | 3 turns | No spells |
| Curse | 5 turns | -20% all stats |
| Fear | 3 turns | Must flee |

### Positive Status Effects
| Effect | Duration | Impact |
|--------|----------|--------|
| Regeneration | 5 turns | 1d4 HP/turn |
| Haste | 3 turns | +30% speed |
| Shield | 3 turns | Absorb 20 damage |
| Invisibility | 2 turns | Undetected |
| Bless | 5 turns | +10% all stats |

---

## AI Behavior

### Combat Intelligence
| Type | Behavior |
|------|-----------|
| Aggressive | Focus on weakest target |
| Defensive | Protect allies, use shields |
| Tactical | Target player weaknesses |
| Retreat | Flee when low HP |
| Support | Heal/buff allies |

### Pack Tactics
- **Wolves**: Surround and flank
- **Goblins**: Bait and ambush
- **Skeletons**: Formation fighting
- **Demons**: Hit and run

---

## Combat Formulas

### Damage Calculation
```
Base Damage = Weapon Damage + STR modifier
Modifier = 1 + (element bonus) + (stance bonus) + (combo bonus)
Defense = Armor + DEX modifier
Final Damage = Base Damage * Modifier - Defense
```

### Accuracy
```
Hit Chance = Base (75%) + DEX bonus - Enemy AGI bonus
Critical = Base (5%) + DEX/10 + Weapon bonus
```

### Experience
```
Combat XP = Enemy Level * 10 * Difficulty Modifier
Bonus XP = First kill, no damage taken, speed kill
```

---

## Unique Mechanics

### Blood/Scent Tracking
- Injured enemies leave blood trails
- Predators attracted to blood
- Can track wounded prey
- Blood magic uses spilled blood

### Adrenaline System
- Low HP triggers adrenaline
- +20% damage, +10% speed
- Duration: 3 turns
- Can stack with other buffs

### Fear System
- Low HP causes fear
- Flee from combat
- Can be resisted with Will
- Intimidation causes fear

### Deathblow System
- Triggers on enemies below 10% HP
- Special finisher move
- Bonus loot chance
- Dramatic animation

---

This provides deep tactical combat with meaningful choices each turn.
