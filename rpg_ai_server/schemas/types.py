from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .enums import (
    DamageType,
    DiceType,
    EntityType,
    ItemCategory,
    OreType,
    SkillType,
    Terrain,
    TimeOfDay,
)


class GridCell(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Items found in this grid cell (swords, armour, etc.)")
    ores: List[OreType] = Field(default_factory=list, description="Predicted ores in this cell")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Entities in this cell (monsters, animals)")
    terrain: Terrain = Field(default=Terrain.UNKNOWN, description="Biome of this cell")
    prerequisites: List[str] = Field(default_factory=list, description="Requirements to traverse this biome")
    cell: tuple[int, int] = Field(default=(0, 0), description="Grid coordinates (x, y)")
    description: str = Field(default="", max_length=200, description="Two-line max description")


class ImageData(BaseModel):
    image_uuid: str = Field(..., description="UUID of the image")
    game_uuid: str = Field(..., description="UUID of the owning game")
    url: str = Field(default="", description="URL or base64 of the image")
    format: str = Field(default="webp", description="Image format")
    timestamp: float = Field(default=0.0, description="When the image was processed")
    grid: List[GridCell] = Field(default_factory=list, description="15x15 grid analysis")
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class GameRequest(BaseModel):
    uuid: str = Field(..., description="Unique request identifier")
    prompt: str = Field(..., description="User prompt")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional game data")
    images: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: float = Field(default=0.0)


class GameOutput(BaseModel):
    uuid: str = Field(..., description="Matching request UUID")
    game_data: Dict[str, Any] = Field(default_factory=dict)
    story: str = Field(default="", description="Generated story response")
    context_summary: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default=0.0)


class DiceRoll(BaseModel):
    dice: DiceType = Field(default=DiceType.D20)
    count: int = Field(default=1, ge=1, le=100)
    advantage: bool = Field(default=False)
    disadvantage: bool = Field(default=False)
    modifier: int = Field(default=0)
    results: List[int] = Field(default_factory=list)
    total: int = Field(default=0)
    reason: str = Field(default="")


class DamageCalculation(BaseModel):
    base_damage: int = Field(default=0, ge=0)
    damage_type: DamageType = Field(default=DamageType.BLUDGEONING)
    multiplier: float = Field(default=1.0, ge=0.0)
    elemental_advantage: float = Field(default=1.0, ge=0.0)
    position_advantage: float = Field(default=1.0, ge=0.0)
    total_damage: float = Field(default=0.0)
    description: str = Field(default="")


class CharacterStats(BaseModel):
    level: int = Field(default=1, ge=1)
    experience: int = Field(default=0, ge=0)
    experience_to_next: int = Field(default=100, ge=1)
    health: int = Field(default=100)
    max_health: int = Field(default=100)
    mana: int = Field(default=50)
    max_mana: int = Field(default=50)
    strength: int = Field(default=10, ge=1, description="Strength stat for carry capacity & melee")
    skills: Dict[SkillType, int] = Field(default_factory=lambda: {s: 1 for s in SkillType})
    stat_cap: int = Field(default=10, description="Max stat points per level bracket")
    attribute_points: int = Field(default=0)
    damage_resistances: Dict[DamageType, float] = Field(default_factory=dict)
    carry_capacity: float = Field(default=50.0, ge=0, description="Max weight in lbs (STR * 5)")
    current_load: float = Field(default=0.0, ge=0, description="Current carried weight in lbs")


class Skill(BaseModel):
    name: str = Field(..., description="Skill name")
    skill_type: SkillType
    cooldown: int = Field(default=0, ge=0, description="Current cooldown in turns")
    max_cooldown: int = Field(default=3, ge=1)
    level: int = Field(default=1, ge=1)
    description: str = Field(default="")
    is_passive: bool = Field(default=False)


class InventoryItem(BaseModel):
    item_id: str = Field(..., description="Unique item identifier")
    name: str = Field(..., description="Item display name")
    category: ItemCategory = Field(default=ItemCategory.MATERIAL)
    quantity: int = Field(default=1, ge=0)
    weight: float = Field(default=1.0, ge=0, description="Weight per unit in lbs")
    damage: int = Field(default=0)
    durability: int = Field(default=100)
    max_durability: int = Field(default=100)
    description: str = Field(default="")
    properties: Dict[str, Any] = Field(default_factory=dict)
    stored_in: Optional[str] = Field(default=None, description="Name of container item holding this, for weight reduction")


class Relationship(BaseModel):
    entity_name: str = Field(..., description="Name of the entity/character")
    disposition: float = Field(default=0.0, ge=-100.0, le=100.0, description="-100 hostile, 0 neutral, 100 friendly")
    description: str = Field(default="", max_length=200)
    last_interaction: float = Field(default=0.0)
    quest_related: bool = Field(default=False)


class ContextSummary(BaseModel):
    active_quests: List[str] = Field(default_factory=list)
    current_location: str = Field(default="unknown")
    party_members: List[str] = Field(default_factory=list)
    recent_events: List[str] = Field(default_factory=list, max_length=20)
    inventory_summary: Dict[str, int] = Field(default_factory=dict)
    key_items: List[str] = Field(default_factory=list)
    time_of_day: TimeOfDay = Field(default=TimeOfDay.DAY)
    weather: str = Field(default="clear")
    narrative_context: str = Field(default="", max_length=500)


class ReDescriptionData(BaseModel):
    uuid: str
    previous_grid_data: List[GridCell] = Field(default_factory=list)
    time_change: str = Field(default="")
    new_entities: List[Dict[str, Any]] = Field(default_factory=list)
    description: str = Field(default="")


class NodeDecision(BaseModel):
    should_search: bool = Field(default=False)
    search_query: str = Field(default="")
    should_process_images: bool = Field(default=False)
    image_uuids: List[str] = Field(default_factory=list)
    should_redescribe: bool = Field(default=False)
    redescribe_uuids: List[str] = Field(default_factory=list)
