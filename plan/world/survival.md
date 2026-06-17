# Survival & Economy System

## Overview

Survival mechanics add realism and challenge, while the economy system provides meaningful resource management and trade.

## Survival Mechanics

### Hunger System

| Hunger Level | Effect | Threshold |
|--------------|--------|-----------|
| Full | +5% all stats | 90-100% |
| Satisfied | Normal | 60-89% |
| Hungry | -10% stamina regen | 30-59% |
| Starving | -20% all stats | 10-29% |
| Dying | -50% all stats, 1 HP/turn | 1-9% |
| Dead | Death | 0% |

### Food Types

| Food | Hunger Restored | Buffs | Rarity |
|------|----------------|-------|--------|
| Apple | 10% | None | Common |
| Bread | 20% | +5 stamina | Common |
| Cheese | 15% | None | Common |
| Meat | 30% | +10% damage | Uncommon |
| Fish | 25% | +5% speed | Uncommon |
| Stew | 40% | +10% all stats | Rare |
| Feast | 60% | +20% all stats | Rare |
| Exotic Food | 50% | Random buff | Epic |
| Legendary Feast | 80% | +30% all stats | Legendary |

### Thirst System

| Thirst Level | Effect | Threshold |
|--------------|--------|-----------|
| Hydrated | +5% mana regen | 90-100% |
| Quenched | Normal | 60-89% |
| Thirsty | -10% mana regen | 30-59% |
| Dehydrated | -20% all stats | 10-29% |
| Dying | -50% all stats, 1 HP/turn | 1-9% |
| Dead | Death | 0% |

### Drink Types

| Drink | Thirst Restored | Buffs | Rarity |
|-------|-----------------|-------|--------|
| Water | 30% | None | Common |
| Juice | 25% | +5% mana regen | Common |
| Ale | 20% | +10% damage, -5% accuracy | Common |
| Wine | 25% | +5% all stats | Uncommon |
| Mead | 30% | +10% stamina | Uncommon |
| Potion | 40% | Random buff | Rare |
| Elixir | 50% | +20% all stats | Epic |
| Nectar | 70% | +30% all stats | Legendary |

### Temperature System

| Temperature | Effect | Survival Time |
|-------------|--------|---------------|
| Below -30 | -30% speed, frostbite | 1 hour |
| -30 to -10 | -20% speed | 4 hours |
| -10 to 0 | -10% speed | 8 hours |
| 0 to 40 | Normal | Unlimited |
| 40 to 60 | -10% stamina | 4 hours |
| 60 to 80 | -20% stamina, dehydration | 2 hours |
| Above 80 | -30% stamina, fire damage | 1 hour |

### Temperature Management

| Item | Effect | Duration |
|------|--------|----------|
| Warm Clothing | +20 cold resist | Always |
| Fire Cape | +50 cold resist | Always |
| Heat Shield | +20 heat resist | Always |
| Fire Resistance | +50 heat resist | 1 hour |
| Campfire | +30 cold resist | While near |
| Shade | +20 heat resist | While near |

### Stamina System

| Action | Stamina Cost |
|--------|--------------|
| Walking | 1/minute |
| Running | 5/minute |
| Swimming | 10/minute |
| Climbing | 8/minute |
| Fighting | 5/attack |
| Blocking | 3/block |
| Dodging | 4/dodge |
| Spellcasting | 3-10/spell |

### Stamina Recovery

| Activity | Recovery Rate |
|----------|---------------|
| Standing | 1/minute |
| Walking | 2/minute |
| Sitting | 5/minute |
| Sleeping | 10/minute |
| Resting | 8/minute |
| Meditation | 12/minute |

### Sleep System

| Sleep Quality | Effect | Requirement |
|---------------|--------|-------------|
| Poor | -10% all stats | Uncomfortable bed |
| Normal | Normal | Bed |
| Good | +5% all stats | Good bed |
| Excellent | +10% all stats | Luxury bed |
| Perfect | +15% all stats, dream | Magical bed |

### Dream Mechanics

| Dream Type | Effect | Trigger |
|------------|--------|---------|
| Normal | None | Random |
| Nightmare | -5% stamina next day | Low HP |
| Prophetic | Reveal future event | High wisdom |
| Lucid | +10% XP next day | High wisdom |
| Magical | Learn spell | Magical location |
| Legendary | Unique ability | Quest completion |

### Disease System

| Disease | Effect | Cure |
|---------|--------|------|
| Common Cold | -10% stamina regen | Rest |
| Flu | -20% all stats | Potion |
| Poison | 1d6 damage/turn | Antidote |
| Curse | -10% all stats | Remove Curse |
| Madness | Random actions | Heal |
| Plague | -30% all stats, spreading | Rare potion |
| vampirism | -50% holy resist, +life steal | Quest |
| Lycanthropy | Transform at full moon | Quest |

### Poison System

| Poison | Damage | Effect | Duration |
|--------|--------|--------|----------|
| Basic Poison | 1/turn | None | 3 turns |
| Deadly Poison | 3/turn | -2 STR | 5 turns |
| Paralytic | 0 | Stun | 2 turns |
| Hallucinogenic | 0 | Confusion | 4 turns |
| Lethal | 5/turn | Death | 3 turns |
| Cursed | 2/turn | -10% all stats | 10 turns |

### Addiction System

| Substance | Effect | Addiction Chance | Withdrawal |
|-----------|--------|------------------|------------|
| Alcohol | +10% damage, -5% accuracy | 20% | -10% all stats |
| Drugs | +20% speed, -10% defense | 30% | -20% all stats |
| Potions | Random buff | 10% | -5% all stats |
| Magic | +30% magic damage | 40% | -30% magic |
| Rare Herbs | +15% all stats | 25% | -15% all stats |

### Encumbrance System

| Weight | Effect | Threshold |
|--------|--------|-----------|
| Light | Normal | 0-30% capacity |
| Medium | -10% speed | 31-60% capacity |
| Heavy | -20% speed, -10% dodge | 61-90% capacity |
| Overloaded | -40% speed, -30% dodge | 91-100% capacity |
| Immobile | Cannot move | 100%+ capacity |

### Carry Capacity

- Base: 100 pounds
- +10 per STR point
- +5 per level
- Gear reduces capacity
- Bags of holding increase capacity

## Economy System

### Currency Types

| Currency | Source | Use |
|----------|--------|-----|
| Copper | Common drops | Basic items |
| Silver | Uncommon drops | Medium items |
| Gold | Rare drops | Rare items |
| Platinum | Epic drops | Epic items |
| Mythril | Legendary drops | Legendary items |
| Soul Essence | Bosses | Special items |
| Reputation | Quests | Faction items |
| Karma | Actions | Special items |

### Shop Types

| Shop | Buys | Sells | Prices |
|------|------|-------|--------|
| General | Everything | Basic items | Normal |
| Weapon | Weapons | Weapons | +10% |
| Armor | Armor | Armor | +10% |
| Magic | Magical items | Potions, scrolls | +15% |
| Blacksmith | Metal items | Weapons, armor | +5% |
| Alchemist | Herbs, ingredients | Potions | +10% |
| Enchanter | Enchanting items | Enchanted gear | +20% |
| Trader | Rare items | Rare items | +25% |
| Fence | Stolen goods | Stolen goods | +30% |

### Dynamic Pricing

| Factor | Price Change |
|--------|--------------|
| Supply/Demand | ±20% |
| Reputation | ±15% |
| Karma | ±10% |
| Season | ±10% |
| Event | ±25% |
| Negotiation | ±10% |

### Bartering System

- Trade items directly with NPCs
- Value based on item stats
- Rare items worth more
- NPC preferences affect trades
- Successful barter improves relationship

### Auction House

- Player-driven market
- List items for sale
- Bid on items
- 5% transaction fee
- Price history tracking

### Taxation System

| Tax | Rate | Purpose |
|-----|------|---------|
| Sales Tax | 5% | Kingdom funds |
| Property Tax | 10% annually | Land ownership |
| Import Tax | 10% | Foreign goods |
| Export Tax | 5% | Local goods |
| Luxury Tax | 15% | Expensive items |

### Investment System

| Investment | Cost | Return |
|------------|------|--------|
| Shop | 1000 gold | 10% weekly |
| Farm | 500 gold | 5% weekly |
| Mine | 2000 gold | 15% weekly |
| Tavern | 1500 gold | 12% weekly |
| Trading Post | 3000 gold | 20% weekly |

### Smuggling System

- Illegal goods worth more
- Higher risk of capture
- Guard patrols
- Hidden routes
- Black market access

### Bounty System

| Bounty Type | Reward | Requirement |
|-------------|--------|-------------|
| Animal | 10-50 gold | Kill animal |
| Monster | 50-200 gold | Kill monster |
| Bandit | 100-500 gold | Kill bandit |
| Boss | 500-2000 gold | Kill boss |
| Player | Variable | PvP |

### Gambling System

| Game | Minimum Bet | Max Win | Skill Factor |
|------|-------------|---------|--------------|
| Dice | 1 copper | 10x bet | Luck |
| Cards | 5 copper | 20x bet | Strategy |
| Roulette | 10 copper | 35x bet | Luck |
| Slots | 1 copper | 100x bet | Luck |
| Arena | 100 copper | 50x bet | Combat |

## Resource Systems

### Mana System

| Mana Type | Regen Rate | Max |
|-----------|------------|-----|
| Natural | 1/minute | INT*2 |
| Meditation | 5/minute | INT*2 |
| Potion | Instant | 50-200 |
| Equipment | +1-10/minute | +10-100 |

### Stamina Regeneration

| Activity | Regen Rate |
|----------|------------|
| Standing | 1/minute |
| Walking | 2/minute |
| Sitting | 5/minute |
| Sleeping | 10/minute |
| Resting | 8/minute |
| Meditation | 12/minute |

### Health Regeneration

| Condition | Regen Rate |
|-----------|------------|
| Out of combat | 5% HP/minute |
| In combat | 1% HP/minute |
| Resting | 10% HP/minute |
| Sleeping | 20% HP/minute |
| Healing spell | 10-50 HP/spell |

### Experience Multipliers

| Source | Multiplier |
|--------|------------|
| First kill | 2x |
| No damage taken | 1.5x |
| Speed kill | 1.25x |
| Combo kills | 1.1x per kill |
| Group kill | 1.5x |
| Quest completion | 2x |
| Discovery | 3x |

### Resource Gathering

| Resource | Tool Required | Skill Required |
|----------|---------------|----------------|
| Wood | Axe | Lumberjacking |
| Stone | Pickaxe | Mining |
| Iron | Pickaxe | Mining 10 |
| Gold | Pickaxe | Mining 30 |
| Mithril | Pickaxe | Mining 50 |
| Herbs | Knife | Herbalism |
| Leather | Knife | Skinning |
| Fish | Fishing rod | Fishing |

## Trading System

### Trade Routes

| Route | Profit | Risk | Time |
|-------|--------|------|------|
| Local | 5% | Low | 1 day |
| Regional | 10% | Medium | 3 days |
| National | 20% | High | 7 days |
| International | 40% | Very High | 14 days |
| Smuggling | 100% | Extreme | 7 days |

### Caravan System

- Hire guards
- Protect goods
- Multiple traders
- Risk of ambush
- Group travel benefits

### Merchant NPCs

| Type | Stock | Prices | Special |
|------|-------|--------|---------|
| Peddler | Random | +20% | Rare finds |
| Trader | Regional | +10% | Bulk discounts |
| Merchant | National | Normal | Reliable stock |
| Importer | International | -10% | Rare items |
| Black Market | Illegal | +50% | Stolen goods |

---

This survival and economy system provides meaningful resource management and trade opportunities.
