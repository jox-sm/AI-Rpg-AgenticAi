# Text-Based RPG Poisons

## Basic Poisons

### Weak Poison
- **ID**: weak_poison
- **Type**: Ingestion
- **Damage**: 1d4 per turn
- **Effect**: Reduces healing received by 25%
- **Duration**: 3 turns
- **Cure**: Antidote or rest
- **Rarity**: Common
- **Required Level**: 1
- **Source**: Starting areas, herbal shops

### Poison
- **ID**: poison
- **Type**: Injury
- **Damage**: 2d6 per turn
- **Effect**: Reduces all stats by 10%
- **Duration**: 5 turns
- **Cure**: Antidote
- **Rarity**: Common
- **Required Level**: 3
- **Source**: Herbalists, early dungeons

### Deadly Poison
- **ID**: deadly_poison
- **Type**: Injury
- **Damage**: 4d6 per turn
- **Effect**: -20% to all stats
- **Duration**: 4 turns
- **Cure**: Strong Antidote
- **Rarity**: Uncommon
- **Required Level**: 8
- **Source**: Assassins guilds, rare drops

### Lethal Poison
- **ID**: lethal_poison
- **Type**: Ingestion
- **Damage**: 6d8 per turn
- **Effect**: Cannot use abilities
- **Duration**: 3 turns
- **Cure**: Master Antidote
- **Rarity**: Rare
- **Required Level**: 15
- **Source**: Elite dungeons, master poisoners

### Venomous Bite
- **ID**: venomous_bite
- **Type**: Injury
- **Damage**: 1d8 per turn
- **Effect**: Slow movement speed by 30%
- **Duration**: 4 turns
- **Cure**: Antidote
- **Rarity**: Common
- **Required Level**: 2
- **Source**: Beast monsters, wilderness areas

### Snake Venom
- **ID**: snake_venom
- **Type**: Injury
- **Damage**: 2d4 per turn
- **Effect**: Chance to miss next attack
- **Duration**: 3 turns
- **Cure**: Antidote
- **Rarity**: Common
- **Required Level**: 3
- **Source**: Snake enemies, desert zones

### Spider Venom
- **ID**: spider_venom
- **Type**: Injury
- **Damage**: 1d6 per turn
- **Effect**: Reduces accuracy by 15%
- **Duration**: 5 turns
- **Cure**: Antidote
- **Rarity**: Common
- **Required Level**: 4
- **Source**: Spider enemies, cave dungeons

### Scorpion Sting
- **ID**: scorpion_sting
- **Type**: Injury
- **Damage**: 2d4+2 per turn
- **Effect**: Causes brief paralysis (1 turn stun)
- **Duration**: 3 turns
- **Cure**: Antidote
- **Rarity**: Common
- **Required Level**: 5
- **Source**: Scorpion enemies, desert dungeons

### Assassin's Blade
- **ID**: assassin_blade
- **Type**: Injury
- **Damage**: 3d6 per turn
- **Effect**: Silences target for 2 turns
- **Duration**: 4 turns
- **Cure**: Strong Antidote
- **Rarity**: Uncommon
- **Required Level**: 10
- **Source**: Assassins guild, rare quest rewards

### Toxic Sludge
- **ID**: toxic_sludge
- **Type**: Contact
- **Damage**: 1d10 per turn
- **Effect**: Corrodes armor, -10% defense
- **Duration**: 5 turns
- **Cure**: Strong Antidote
- **Rarity**: Common
- **Required Level**: 6
- **Source**: Sewer dungeons, sludge enemies

### Noxious Fumes
- **ID**: noxious_fumes
- **Type**: Inhaled
- **Damage**: 2d4 per turn
- **Effect**: Causes nausea, -25% damage output
- **Duration**: 3 turns
- **Cure**: Fresh air + Antidote
- **Rarity**: Common
- **Required Level**: 7
- **Source**: Swamp zones, poison gas traps

### Plague Toxin
- **ID**: plague_toxin
- **Type**: Ingestion
- **Damage**: 1d12 per turn
- **Effect**: Spread to nearby allies (50% chance)
- **Duration**: 6 turns
- **Cure**: Master Antidote + Purification
- **Rarity**: Rare
- **Required Level**: 12
- **Source**: Undead zones, plague monsters

### Corruption Venom
- **ID**: corruption_venom
- **Type**: Injury
- **Damage**: 3d4 per turn
- **Effect**: Corrupts healing, heals become damage over time
- **Duration**: 4 turns
- **Cure**: Purification spell
- **Rarity**: Uncommon
- **Required Level**: 14
- **Source**: Demonic areas, corrupted beasts

### Black Lotus Extract
- **ID**: black_lotus
- **Type**: Ingestion
- **Damage**: 5d4 per turn
- **Effect**: Halves all resistances
- **Duration**: 4 turns
- **Cure**: Master Antidote
- **Rarity**: Rare
- **Required Level**: 16
- **Source**: Rare herb gathering, black market

### Nightshade Toxin
- **ID**: nightshade
- **Type**: Ingestion
- **Damage**: 4d6 per turn
- **Effect**: Causes hallucinations, random target attacks
- **Duration**: 3 turns
- **Cure**: Strong Antidote
- **Rarity**: Uncommon
- **Required Level**: 11
- **Source**: Dark forest zones, herbal shops

---

## Elemental Poisons

### Fire Venom
- **ID**: fire_poison
- **Type**: Injury
- **Damage**: 2d6+2 fire per turn
- **Effect**: Applies burn, additional 1d4 fire damage
- **Duration**: 4 turns
- **Cure**: Fire Resistance Potion + Antidote
- **Rarity**: Uncommon
- **Required Level**: 8
- **Source**: Fire dungeons, flame serpents

### Ice Toxin
- **ID**: ice_poison
- **Type**: Contact
- **Damage**: 2d6 cold per turn
- **Effect**: Slows movement by 50%, chance to freeze
- **Duration**: 4 turns
- **Cure**: Fire Resistance Potion
- **Rarity**: Uncommon
- **Required Level**: 9
- **Source**: Ice caves, frost elementals

### Lightning Essence
- **ID**: lightning_poison
- **Type**: Contact
- **Damage**: 3d4 lightning per turn
- **Effect**: Stuns target for 1 turn every 2 turns
- **Duration**: 3 turns
- **Cure**: Grounding Potion
- **Rarity**: Rare
- **Required Level**: 12
- **Source**: Storm dungeons, lightning elementals

### Acidic Venom
- **ID**: acid_poison
- **Type**: Contact
- **Damage**: 2d8 acid per turn
- **Effect**: -30% armor, corrodes weapons
- **Duration**: 5 turns
- **Cure**: Strong Antidote + Neutralize
- **Rarity**: Rare
- **Required Level**: 13
- **Source**: Acid swamps, sludge monsters

### Shadow Venom
- **ID**: shadow_poison
- **Type**: Magical
- **Damage**: 3d4 shadow per turn
- **Effect**: Reduces evasion by 40%
- **Duration**: 4 turns
- **Cure**: Light Potion + Purification
- **Rarity**: Rare
- **Required Level**: 14
- **Source**: Shadow realm, dark mages

### Nature's Wrath
- **ID**: nature_poison
- **Type**: Contact
- **Damage**: 2d6 nature per turn
- **Effect**: Roots target in place for 2 turns
- **Duration**: 5 turns
- **Cure**: Fire Potion + Antidote
- **Rarity**: Uncommon
- **Required Level**: 10
- **Source**: Forest dungeons, nature spirits

### Volcanic Toxin
- **ID**: volcanic_poison
- **Type**: Contact
- **Damage**: 4d4 fire+physical per turn
- **Effect**: Burns equipment, -15% all stats
- **Duration**: 3 turns
- **Cure**: Master Antidote + Fire Resistance
- **Rarity**: Rare
- **Required Level**: 16
- **Source**: Volcano dungeons, fire giants

### Frost Bite Venom
- **ID**: frost_poison
- **Type**: Injury
- **Damage**: 3d4 cold per turn
- **Effect**: Freezes 1 equipped item, cannot use
- **Duration**: 4 turns
- **Cure**: Warmth Potion + Antidote
- **Rarity**: Uncommon
- **Required Level**: 11
- **Source**: Tundra zones, ice wolves

### Storm Venom
- **ID**: storm_poison
- **Type**: Inhaled
- **Damage**: 2d6 lightning+wind per turn
- **Effect**: Disrupts magic casting, 50% spell failure
- **Duration**: 3 turns
- **Cure**: Calm Weather Potion
- **Rarity**: Rare
- **Required Level**: 15
- **Source**: Storm peaks, thunderbirds

### Void Poison
- **ID**: void_poison
- **Type**: Magical
- **Damage**: 5d4 void per turn
- **Effect**: Nullifies one buff per turn
- **Duration**: 4 turns
- **Cure**: Void Ward Potion
- **Rarity**: Epic
- **Required Level**: 20
- **Source**: Void rifts, void creatures

### Abyssal Venom
- **ID**: abyssal_poison
- **Type**: Magical
- **Damage**: 4d6 dark per turn
- **Effect**: Drains mana equal to damage dealt
- **Duration**: 3 turns
- **Cure**: Light Potion + Mana Restoration
- **Rarity**: Rare
- **Required Level**: 17
- **Source**: Abyss dungeons, shadow lords

### Solar Burn
- **ID**: solar_burn
- **Type**: Contact
- **Damage**: 4d4 radiant per turn
- **Effect**: Undead take double damage, living are blinded
- **Duration**: 3 turns
- **Cure**: Shade Potion + Antidote
- **Rarity**: Uncommon
- **Required Level**: 13
- **Source**: Holy temples, celestial creatures

---

## Status Poisons

### Paralytic Venom
- **ID**: paralytic_poison
- **Type**: Injury
- **Damage**: 1d4 per turn
- **Effect**: Cannot move or attack for 1 turn, then slowed
- **Duration**: 4 turns
- **Cure**: Strong Antidote
- **Rarity**: Uncommon
- **Required Level**: 9
- **Source**: Paralysis snakes, rogue assassins

### Confusion Toxin
- **ID**: confusion_poison
- **Type**: Inhaled
- **Damage**: 0 per turn
- **Effect**: Attacks random targets, 50% chance to hit allies
- **Duration**: 4 turns
- **Cure**: Clarity Potion
- **Rarity**: Uncommon
- **Required Level**: 10
- **Source**: Fey creatures, illusion dungeons

### Sleep Venom
- **ID**: sleep_poison
- **Type**: Contact
- **Damage**: 0 per turn
- **Effect**: Falls asleep, wakes on damage
- **Duration**: 3 turns
- **Cure**: Wakefulness Potion
- **Rarity**: Uncommon
- **Required Level**: 8
- **Source**: Fae zones, dream spiders

### Blindness Toxin
- **ID**: blind_poison
- **Type**: Contact
- **Damage**: 1d2 per turn
- **Effect**: Cannot see, -80% accuracy
- **Duration**: 5 turns
- **Cure**: Sight Restoration Potion
- **Rarity**: Uncommon
- **Required Level**: 9
- **Source**: Dark caves, blind monsters

### Silence Venom
- **ID**: silence_poison
- **Type**: Inhaled
- **Damage**: 0 per turn
- **Effect**: Cannot cast spells or use abilities
- **Duration**: 4 turns
- **Cure**: Voice Potion + Antidote
- **Rarity**: Rare
- **Required Level**: 12
- **Source**: Silent monks, anti-mage zones

### Slow Toxin
- **ID**: slow_poison
- **Type**: Contact
- **Damage**: 1d3 per turn
- **Effect**: -60% movement and attack speed
- **Duration**: 5 turns
- **Cure**: Haste Potion + Antidote
- **Rarity**: Common
- **Required Level**: 6
- **Source**: Slow monsters, swamps

### Stun Venom
- **ID**: stun_poison
- **Type**: Injury
- **Damage**: 2d2 per turn
- **Effect**: Cannot act for 1 turn
- **Duration**: 3 turns
- **Cure**: Strong Antidote
- **Rarity**: Uncommon
- **Required Level**: 11
- **Source**: Stun insects, arena fighters

### Fear Toxin
- **ID**: fear_poison
- **Type**: Inhaled
- **Damage**: 0 per turn
- **Effect**: Target flees for 2 turns, then -30% all stats
- **Duration**: 4 turns
- **Cure**: Courage Potion
- **Rarity**: Uncommon
- **Required Level**: 10
- **Source**: Horror dungeons, fear wraiths

### Weakness Venom
- **ID**: weakness_poison
- **Type**: Contact
- **Damage**: 0 per turn
- **Effect**: -40% attack damage for duration
- **Duration**: 6 turns
- **Cure**: Strength Potion + Antidote
- **Rarity**: Common
- **Required Level**: 5
- **Source**: Weakling monsters, cursed items

### Curse Toxin
- **ID**: curse_poison
- **Type**: Magical
- **Damage**: 1d4 dark per turn
- **Effect**: Doubles all damage taken from curses
- **Duration**: 5 turns
- **Cure**: Remove Curse + Antidote
- **Rarity**: Rare
- **Required Level**: 14
- **Source**: Cursed tombs, dark witches

### Berserk Venom
- **ID**: berserk_poison
- **Type**: Ingestion
- **Damage**: 0 per turn
- **Effect**: +50% damage but -50% defense, attacks random targets
- **Duration**: 4 turns
- **Cure**: Calm Potion
- **Rarity**: Uncommon
- **Required Level**: 12
- **Source**: Berserker camps, rage beasts

### Madness Venom
- **ID**: madness_poison
- **Type**: Inhaled
- **Damage**: 2d2 psychic per turn
- **Effect**: Random ability usage, 30% chance to use ultimate
- **Duration**: 5 turns
- **Cure**: Sanity Potion + Purification
- **Rarity**: Rare
- **Required Level**: 16
- **Source**: Mad king's dungeon, chaos creatures

### Drain Toxin
- **ID**: drain_poison
- **Type**: Contact
- **Damage**: 3d2 per turn
- **Effect**: Drains mana equal to damage dealt
- **Duration**: 4 turns
- **Cure**: Mana Restoration + Antidote
- **Rarity**: Uncommon
- **Required Level**: 11
- **Source**: Mana leeches, mage towers

### Charm Venom
- **ID**: charm_poison
- **Type**: Contact
- **Damage**: 0 per turn
- **Effect**: Becomes temporary ally of caster for 3 turns
- **Duration**: 3 turns
- **Cure**: Dispel Magic + Antidote
- **Rarity**: Rare
- **Required Level**: 15
- **Source**: Fey courts, charm mages

### Petrify Toxin
- **ID**: petrify_poison
- **Type**: Contact
- **Damage**: 0 per turn
- **Effect**: Gradually turns to stone, -20% speed per turn
- **Duration**: 5 turns
- **Cure**: Stone Curing Potion
- **Rarity**: Rare
- **Required Level**: 18
- **Source**: Gorgon caves, stone golems

---

## Magical Poisons

### Mana Drain
- **ID**: mana_poison
- **Type**: Magical
- **Damage**: 0 physical per turn
- **Effect**: Drains 5% max mana per turn
- **Duration**: 6 turns
- **Cure**: Mana Restoration + Purification
- **Rarity**: Uncommon
- **Required Level**: 10
- **Source**: Mana leeches, mage dungeons

### Soul Rot
- **ID**: soul_poison
- **Type**: Magical
- **Damage**: 3d4 spiritual per turn
- **Effect**: Reduces max HP by 5% per turn
- **Duration**: 5 turns
- **Cure**: Soul Restoration + Greater Healing
- **Rarity**: Rare
- **Required Level**: 16
- **Source**: Soul collectors, death knights

### Essence Corruptor
- **ID**: essence_poison
- **Type**: Magical
- **Damage**: 2d6 per turn
- **Effect**: Transforms 10% of healing into damage
- **Duration**: 4 turns
- **Cure**: Purification + Essence Cleanse
- **Rarity**: Rare
- **Required Level**: 15
- **Source**: Essence wraiths, corrupted zones

### Arcane Bane
- **ID**: arcane_poison
- **Type**: Magical
- **Damage**: 4d4 arcane per turn
- **Effect**: Spells cost 50% more mana
- **Duration**: 4 turns
- **Cure**: Arcane Cleanse + Antidote
- **Rarity**: Rare
- **Required Level**: 14
- **Source**: Anti-mage towers, arcane constructs

### Eldritch Venom
- **ID**: eldritch_poison
- **Type**: Magical
- **Damage**: 5d4 psychic per turn
- **Effect**: Sanity check each turn, failure causes confusion
- **Duration**: 4 turns
- **Cure**: Sanity Potion + Greater Purification
- **Rarity**: Epic
- **Required Level**: 20
- **Source**: Eldritch horrors, void rifts

### Cosmic Toxin
- **ID**: cosmic_poison
- **Type**: Magical
- **Damage**: 4d6 cosmic per turn
- **Effect**: Reduces all resistances by 20% per turn
- **Duration**: 4 turns
- **Cure**: Cosmic Ward + Master Antidote
- **Rarity**: Epic
- **Required Level**: 22
- **Source**: Cosmic entities, star forges

### Ethereal Venom
- **ID**: ethereal_poison
- **Type**: Magical
- **Damage**: 3d4 ethereal per turn
- **Effect**: Phases target partially out of reality, -30% all damage
- **Duration**: 3 turns
- **Cure**: Ethereal Anchor + Purification
- **Rarity**: Rare
- **Required Level**: 18
- **Source**: Ethereal plane creatures, ghost towns

### Dimensional Rift Poison
- **ID**: dimensional_poison
- **Type**: Magical
- **Damage**: 6d4 void per turn
- **Effect**: Teleports random ally to another location each turn
- **Duration**: 3 turns
- **Cure**: Dimension Anchor + Greater Antidote
- **Rarity**: Epic
- **Required Level**: 24
- **Source**: Rift creatures, planar dungeons

### Blood Curse
- **ID**: blood_poison
- **Type**: Magical
- **Damage**: 3d6 blood per turn
- **Effect**: Heals caster for 50% of damage dealt
- **Duration**: 4 turns
- **Cure**: Blood Purge + Purification
- **Rarity**: Rare
- **Required Level**: 15
- **Source**: Blood mages, vampire lairs

### Spirit Sever
- **ID**: spirit_poison
- **Type**: Magical
- **Damage**: 4d4 spiritual per turn
- **Effect**: Weakens spirit, -25% to all magical defenses
- **Duration**: 5 turns
- **Cure**: Spirit Mending + Greater Purification
- **Rarity**: Rare
- **Required Level**: 17
- **Source**: Spirit realm, ghost armies

### Fate Weaver's Venom
- **ID**: fate_poison
- **Type**: Magical
- **Damage**: 2d8 destiny per turn
- **Effect**: -15% to all critical chances and dodges
- **Duration**: 5 turns
- **Cure**: Fate Ward + Ancient Antidote
- **Rarity**: Epic
- **Required Level**: 21
- **Source**: Fate weavers, destiny dungeons

### Chaos Miasma
- **ID**: chaos_poison
- **Type**: Inhaled
- **Damage**: 3d4 chaotic per turn
- **Effect**: Random debuff applied each turn
- **Duration**: 4 turns
- **Cure**: Order Potion + Purification
- **Rarity**: Rare
- **Required Level**: 19
- **Source**: Chaos rifts, wild magic zones

### Entropy Venom
- **ID**: entropy_poison
- **Type**: Magical
- **Damage**: 4d4 entropy per turn
- **Effect**: Degrades equipment durability by 10% per turn
- **Duration**: 4 turns
- **Cure**: Stability Potion + Master Antidote
- **Rarity**: Rare
- **Required Level**: 16
- **Source**: Decay zones, entropy elementals

### Void Corruption
- **ID**: void_corruption
- **Type**: Magical
- **Damage**: 5d4 void per turn
- **Effect**: Corrupts 1 equipped item per turn (random)
- **Duration**: 3 turns
- **Cure**: Void Cleanse + Greater Purification
- **Rarity**: Epic
- **Required Level**: 23
- **Source**: Void Lords, corrupted realms

### Abyssal Corruption
- **ID**: abyssal_corruption
- **Type**: Magical
- **Damage**: 4d6 abyssal per turn
- **Effect**: Converts physical damage to shadow damage for caster
- **Duration**: 4 turns
- **Cure**: Abyssal Banishment + Ancient Purification
- **Rarity**: Epic
- **Required Level**: 25
- **Source**: Abyss Lords, deepest dungeons

### Celestial Plague
- **ID**: celestial_plague
- **Type**: Magical
- **Damage**: 3d6 radiant per turn
- **Effect**: Undead take 2x damage, living take 0.5x
- **Duration**: 5 turns
- **Cure**: Celestial Cleansing + Greater Antidote
- **Rarity**: Rare
- **Required Level**: 18
- **Source**: Celestial temples, holy zones

### Temporal Toxin
- **ID**: temporal_poison
- **Type**: Magical
- **Damage**: 2d8 temporal per turn
- **Effect**: -25% to cooldown recovery speed
- **Duration**: 4 turns
- **Cure**: Time Ward + Purification
- **Rarity**: Epic
- **Required Level**: 22
- **Source**: Time rifts, chronomancers

---

## Summary

| Category | Count |
|----------|-------|
| Basic Poisons | 16 |
| Elemental Poisons | 12 |
| Status Poisons | 15 |
| Magical Poisons | 17 |
| **Total** | **60** |
