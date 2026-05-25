from enum import Enum


class Terrain(str, Enum):
    PLAINS = "plains"
    FOREST = "forest"
    DESERT = "desert"
    MOUNTAINS = "mountains"
    SWAMP = "swamp"
    OCEAN = "ocean"
    RIVER = "river"
    CAVE = "cave"
    DUNGEON = "dungeon"
    GRAVEYARD = "graveyard"
    SAVANNA = "savanna"
    TUNDRA = "tundra"
    JUNGLE = "jungle"
    VOLCANO = "volcano"
    CITY = "city"
    RUINS = "ruins"
    UNKNOWN = "unknown"


class TimeOfDay(str, Enum):
    DAWN = "dawn"
    MORNING = "morning"
    DAY = "day"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    NIGHT = "night"
    MIDNIGHT = "midnight"


class EntityType(str, Enum):
    MONSTER = "monster"
    ANIMAL = "animal"
    NPC = "npc"
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    BOSS = "boss"


class ItemCategory(str, Enum):
    WEAPON = "weapon"
    ARMOUR = "armour"
    TOOL = "tool"
    POTION = "potion"
    FOOD = "food"
    MATERIAL = "material"
    KEY_ITEM = "key_item"
    CURRENCY = "currency"
    MAGIC = "magic"


class OreType(str, Enum):
    IRON = "iron"
    COAL = "coal"
    GOLD = "gold"
    DIAMOND = "diamond"
    EMERALD = "emerald"
    COPPER = "copper"
    SILVER = "silver"
    MITHRIL = "mithril"
    ADAMANTITE = "adamantite"
    RUNITE = "runite"
    NONE = "none"


class SkillType(str, Enum):
    ATTACK = "attack"
    DEFENSE = "defense"
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"
    CONSTITUTION = "constitution"
    STEALTH = "stealth"
    PERCEPTION = "perception"
    SURVIVAL = "survival"
    MAGIC = "magic"


class DamageType(str, Enum):
    SLASHING = "slashing"
    PIERCING = "piercing"
    BLUDGEONING = "bludgeoning"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    ACID = "acid"
    POISON = "poison"
    RADIANT = "radiant"
    NECROTIC = "necrotic"
    PSYCHIC = "psychic"
    FORCE = "force"
    THUNDER = "thunder"


class DiceType(str, Enum):
    D4 = "d4"
    D6 = "d6"
    D8 = "d8"
    D10 = "d10"
    D12 = "d12"
    D20 = "d20"
    D100 = "d100"
