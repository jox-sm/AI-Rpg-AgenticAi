from __future__ import annotations

import json
import math
import random
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from ...schemas.enums import DamageType, DiceType, SkillType
from ...schemas.types import (
    CharacterStats,
    DamageCalculation,
    DiceRoll,
    InventoryItem,
    Relationship,
    Skill,
)
from ...utils.logger import logger

DICE_MAP: Dict[DiceType, int] = {
    DiceType.D4: 4,
    DiceType.D6: 6,
    DiceType.D8: 8,
    DiceType.D10: 10,
    DiceType.D12: 12,
    DiceType.D20: 20,
    DiceType.D100: 100,
}

STAT_CAP_TABLE: Dict[int, int] = {
    1: 10, 2: 12, 3: 14, 4: 16, 5: 18,
    6: 20, 7: 22, 8: 24, 9: 26, 10: 30,
}

DAMAGE_TYPE_EFFECTIVENESS: Dict[str, Dict[str, float]] = {
    "fire": {"ice": 2.0, "plant": 1.5, "earth": 0.5, "metal": 0.5},
    "cold": {"fire": 0.5, "plant": 2.0, "water": 0.5, "earth": 1.5},
    "lightning": {"water": 2.0, "metal": 1.5, "earth": 0.5, "air": 0.5},
    "bludgeoning": {"crystal": 2.0, "bone": 1.5, "construct": 0.5},
    "slashing": {"flesh": 1.5, "plant": 0.5, "construct": 0.5},
    "piercing": {"flesh": 1.0, "plate": 0.5, "scale": 0.5},
    "radiant": {"undead": 2.0, "fiend": 2.0, "shadow": 1.5},
    "necrotic": {"living": 1.5, "undead": 0.0, "construct": 0.0},
    "force": {"ethereal": 2.0, "construct": 1.5, "physical": 1.0},
    "psychic": {"beast": 0.5, "construct": 0.0, "humanoid": 1.5},
    "thunder": {"crystal": 2.0, "construct": 1.5, "flesh": 1.0},
    "acid": {"metal": 2.0, "organic": 1.5, "construct": 1.0},
    "poison": {"living": 1.0, "undead": 0.0, "construct": 0.0, "plant": 0.5},
}

MONSTER_DIFFICULTY = {
    "rat": {"exp": 10, "level": 1},
    "goblin": {"exp": 50, "level": 2},
    "skeleton": {"exp": 75, "level": 3},
    "zombie": {"exp": 80, "level": 3},
    "wolf": {"exp": 100, "level": 4},
    "bandit": {"exp": 120, "level": 4},
    "bear": {"exp": 200, "level": 5},
    "ogre": {"exp": 300, "level": 6},
    "wraith": {"exp": 400, "level": 7},
    "troll": {"exp": 500, "level": 8},
    "golem": {"exp": 800, "level": 10},
    "dragon_young": {"exp": 1500, "level": 12},
    "lich": {"exp": 2000, "level": 14},
    "dragon_adult": {"exp": 5000, "level": 18},
    "dragon_ancient": {"exp": 15000, "level": 25},
}

PLAN_QUALITY_BONUSES = {
    "none": {"advantage_bonus": -4, "damage_mult": 0.5, "desc": "No plan, just attacking recklessly"},
    "reckless": {"advantage_bonus": -4, "damage_mult": 0.5, "desc": "Reckless attack with no strategy"},
    "poor": {"advantage_bonus": -2, "damage_mult": 0.7, "desc": "Bad plan that makes the situation worse"},
    "average": {"advantage_bonus": 0, "damage_mult": 1.0, "desc": "Standard attack, nothing special"},
    "good": {"advantage_bonus": 2, "damage_mult": 1.3, "desc": "Decent plan with some tactical thought"},
    "excellent": {"advantage_bonus": 4, "damage_mult": 1.6, "desc": "Smart plan exploiting enemy weaknesses"},
    "genius": {"advantage_bonus": 6, "damage_mult": 2.0, "desc": "Brilliant trap or masterful strategy"},
}

ORGAN_HIT_MULTIPLIERS = {
    "eye": 0.3,
    "head": 0.5,
    "neck": 0.4,
    "heart": 0.2,
    "leg": 0.6,
    "arm": 0.7,
    "wing": 0.5,
    "tail": 0.8,
    "core": 0.25,
}


@tool
async def situational_dice(
    player_level: int,
    plan_quality: str = "average",
    enemy_name: str = "",
    enemy_level: int = 0,
) -> str:
    """Analyze combat situation and recommend optimal dice configuration.
    Evaluates player power vs enemy difficulty plus plan/strategy quality,
    then returns recommended dice type, advantage/disadvantage, and modifier.

    Args:
        player_level: Current character level (required)
        plan_quality: How good the player's described action is:
            'none'/'reckless' - attacking with no plan, making things worse (-4 penalty)
            'poor' - bad approach that hinders success (-2 penalty)
            'average' - standard attack, nothing special (no modifier)
            'good' - decent tactical thinking (+2 bonus)
            'excellent' - smart plan exploiting enemy weaknesses (+4 bonus)
            'genius' - brilliant trap or masterful strategy (+6 bonus)
        enemy_name: Name of enemy to look up in bestiary
        enemy_level: Enemy level if not in bestiary (optional fallback)
    """
    enemy_lvl = enemy_level
    if enemy_name:
        monster_info = MONSTER_DIFFICULTY.get(enemy_name.strip().lower())
        if monster_info:
            enemy_lvl = monster_info["level"]

    if enemy_lvl <= 0:
        enemy_lvl = player_level

    power_ratio = player_level / max(enemy_lvl, 1)
    power_ratio = max(0.1, min(5.0, power_ratio))

    if power_ratio >= 2.0:
        power_bonus = 5
        power_desc = "overwhelming advantage"
    elif power_ratio >= 1.5:
        power_bonus = 3
        power_desc = "clear advantage"
    elif power_ratio >= 1.1:
        power_bonus = 1
        power_desc = "slight advantage"
    elif power_ratio >= 0.9:
        power_bonus = 0
        power_desc = "even match"
    elif power_ratio >= 0.6:
        power_bonus = -2
        power_desc = "slight disadvantage"
    elif power_ratio >= 0.4:
        power_bonus = -4
        power_desc = "clear disadvantage"
    else:
        power_bonus = -6
        power_desc = "overwhelming disadvantage"

    plan_info = PLAN_QUALITY_BONUSES.get(plan_quality.strip().lower(), PLAN_QUALITY_BONUSES["average"])
    plan_bonus = plan_info["advantage_bonus"]
    damage_mult = plan_info["damage_mult"]
    plan_desc = plan_info["desc"]

    total_modifier = power_bonus + plan_bonus

    recommend_advantage = False
    recommend_disadvantage = False
    if total_modifier >= 3:
        recommend_advantage = True
    elif total_modifier <= -3:
        recommend_disadvantage = True

    effective_bonus = total_modifier
    if recommend_advantage:
        effective_bonus = max(0, total_modifier - 3)
    elif recommend_disadvantage:
        effective_bonus = min(0, total_modifier + 3)

    return json.dumps({
        "analysis": f"Player lvl {player_level} vs enemy lvl {enemy_lvl} ({power_desc}). Plan: {plan_desc}.",
        "power_ratio": round(power_ratio, 2),
        "power_bonus": power_bonus,
        "power_description": power_desc,
        "plan_quality": plan_quality,
        "plan_bonus": plan_bonus,
        "plan_damage_multiplier": damage_mult,
        "total_situation_modifier": total_modifier,
        "recommended_dice": "d20",
        "recommended_advantage": recommend_advantage,
        "recommended_disadvantage": recommend_disadvantage,
        "recommended_modifier": effective_bonus,
        "recommended_damage_multiplier": damage_mult,
        "guidance": (
            "Use the recommended dice parameters in your dice_roller call. "
            f"Set modifier={effective_bonus}, advantage={recommend_advantage}, disadvantage={recommend_disadvantage}. "
            f"Apply damage_multiplier of {damage_mult}x to final damage via damage_multiplier tool."
        ),
    }, indent=2)


@tool
async def dice_roller(
    dice: str = "d20",
    count: int = 1,
    advantage: bool = False,
    disadvantage: bool = False,
    modifier: int = 0,
    reason: str = "",
) -> str:
    """Roll D&D dice with optional advantage/disadvantage.

    Args:
        dice: Dice type: d4, d6, d8, d10, d12, d20, d100
        count: Number of dice to roll (1-100)
        advantage: Roll twice, take higher (only for single die)
        disadvantage: Roll twice, take lower (only for single die)
        modifier: Flat modifier to add to total
        reason: Why this roll is being made
    """
    try:
        dice_type = DiceType(dice.lower())
    except ValueError:
        return json.dumps({"error": f"Invalid dice type: {dice}"})

    max_faces = DICE_MAP[dice_type]
    results = []

    if advantage or disadvantage:
        for _ in range(count):
            roll1 = random.randint(1, max_faces)
            roll2 = random.randint(1, max_faces)
            if advantage:
                results.append(max(roll1, roll2))
            else:
                results.append(min(roll1, roll2))
    else:
        for _ in range(count):
            results.append(random.randint(1, max_faces))

    total = sum(results) + modifier
    roll = DiceRoll(
        dice=dice_type,
        count=count,
        advantage=advantage,
        disadvantage=disadvantage,
        modifier=modifier,
        results=results,
        total=total,
        reason=reason,
    )
    return json.dumps(roll.model_dump(), indent=2)


@tool
async def damage_multiplier(
    base_damage: int,
    damage_type: str,
    monster_type: str,
    position_description: str = "",
    is_trapped: bool = False,
    is_restrained: bool = False,
    is_unconscious: bool = False,
) -> str:
    """Calculate damage multiplier based on damage type, monster composition, and positioning.

    Args:
        base_damage: Base damage before multipliers
        damage_type: Type of damage (fire, cold, lightning, bludgeoning, slashing, piercing, radiant, necrotic, force, psychic, thunder, acid, poison)
        monster_type: Type of monster for elemental effectiveness (ice, plant, earth, metal, undead, fiend, construct, flesh, etc.)
        position_description: How the target is positioned (e.g., 'buried under tree', 'in a hole', 'pinned')
        is_trapped: Whether the target is fully trapped
        is_restrained: Whether the target is restrained
        is_unconscious: Whether the target is unconscious
    """
    dt = damage_type.lower()

    elemental_mult = DAMAGE_TYPE_EFFECTIVENESS.get(dt, {}).get(monster_type.lower(), 1.0)

    position_mult = 1.0
    position_desc = position_description.lower()

    if is_unconscious:
        position_mult *= 2.5
    if is_restrained:
        position_mult *= 1.5
    if is_trapped:
        position_mult *= 2.0

    if "hole" in position_desc or "pit" in position_desc:
        position_mult *= 1.3
    if "burn" in position_desc or "fire" in position_desc:
        position_mult *= 1.2
    if "stuck" in position_desc or "pinned" in position_desc:
        position_mult *= 1.4
    if "buried" in position_desc or "crush" in position_desc:
        position_mult *= 1.6

    total_mult = elemental_mult * position_mult
    total_damage = base_damage * total_mult

    calc = DamageCalculation(
        base_damage=base_damage,
        damage_type=DamageType(dt) if dt in DamageType._value2member_map_ else DamageType.BLUDGEONING,
        multiplier=total_mult,
        elemental_advantage=elemental_mult,
        position_advantage=position_mult,
        total_damage=round(total_damage, 1),
        description=f"Elemental x{elemental_mult}, Position x{position_mult} = {round(total_damage, 1)} total",
    )
    return json.dumps(calc.model_dump(), indent=2)


@tool
async def stats_multiplier_and_updater(
    current_stats_json: str,
    monster_name: str = "",
    exp_gained: int = 0,
    monster_difficulty: str = "medium",
    should_level_up: bool = False,
) -> str:
    """Track experience and monster difficulty, level up characters, and update stats.

    Args:
        current_stats_json: JSON string of current CharacterStats
        monster_name: Name of defeated monster
        exp_gained: Experience points gained (if known)
        monster_difficulty: Difficulty rating (easy, medium, hard, boss)
    """
    try:
        stats_dict = json.loads(current_stats_json)
    except (json.JSONDecodeError, TypeError):
        stats_dict = {}

    stats = CharacterStats(**stats_dict)

    if monster_name:
        monster_info = MONSTER_DIFFICULTY.get(monster_name.lower(), None)
        if monster_info:
            exp_gained = monster_info["exp"]
        else:
            difficulty_mult = {"easy": 30, "medium": 75, "hard": 200, "boss": 500}
            exp_gained = difficulty_mult.get(monster_difficulty.lower(), 75)

    stats.experience += exp_gained
    level_ups = 0
    while stats.experience >= stats.experience_to_next:
        stats.experience -= stats.experience_to_next
        stats.level += 1
        level_ups += 1
        stats.experience_to_next = int(stats.experience_to_next * 1.5)
        stats.stat_cap = STAT_CAP_TABLE.get(min(stats.level, 10), stats.stat_cap + 2)
        stats.attribute_points += 2
        stats.max_health += 10 + stats.level
        stats.max_mana += 5 + stats.level // 2

    stats.health = stats.max_health
    stats.mana = stats.max_mana

    if stats.level >= 2:
        stats.stat_cap = STAT_CAP_TABLE.get(stats.level, 10 + (stats.level - 1) * 2)

    return json.dumps(stats.model_dump(), indent=2)


@tool
async def skill_updater_and_validator(
    current_skills_json: str,
    action: str = "check_cooldowns",
    skill_name: str = "",
    new_skill_json: str = "",
    sacrifice_skills: str = "",
) -> str:
    """Update skill cooldowns, validate skill usage, handle new skill acquisition.

    Args:
        current_skills_json: JSON string of current skills array
        action: Action to perform - 'check_cooldowns', 'reduce_cooldowns', 'use_skill', 'add_skill', 'sacrifice_for_new'
        skill_name: Name of the skill being used (for use_skill action)
        new_skill_json: JSON string of new skill to add (for add_skill action)
        sacrifice_skills: Comma-separated skill names to sacrifice (for sacrifice_for_new action)
    """
    try:
        skills_data = json.loads(current_skills_json) if isinstance(current_skills_json, str) else current_skills_json
    except (json.JSONDecodeError, TypeError):
        skills_data = []

    skills = [Skill(**s) if isinstance(s, dict) else s for s in skills_data]

    if action == "reduce_cooldowns":
        for skill in skills:
            if skill.cooldown > 0:
                skill.cooldown -= 1
        return json.dumps([s.model_dump() for s in skills], indent=2)

    elif action == "check_cooldowns":
        available = [s.name for s in skills if s.cooldown == 0 and not s.is_passive]
        on_cooldown = [{"name": s.name, "cooldown": s.cooldown} for s in skills if s.cooldown > 0]
        return json.dumps({"available": available, "on_cooldown": on_cooldown}, indent=2)

    elif action == "use_skill":
        for skill in skills:
            if skill.name == skill_name:
                if skill.cooldown > 0:
                    return json.dumps({"error": f"Skill '{skill_name}' on cooldown for {skill.cooldown} more turns"})
                skill.cooldown = skill.max_cooldown
                return json.dumps({"success": True, "skill": skill.model_dump()}, indent=2)
        return json.dumps({"error": f"Skill '{skill_name}' not found"}, indent=2)

    elif action == "add_skill":
        try:
            new_skill_data = json.loads(new_skill_json) if isinstance(new_skill_json, str) else new_skill_json
            new_skill = Skill(**new_skill_data) if isinstance(new_skill_data, dict) else new_skill_data
            skills.append(new_skill)
            return json.dumps([s.model_dump() for s in skills], indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to add skill: {e}"}, indent=2)

    elif action == "sacrifice_for_new":
        names_to_sacrifice = [n.strip() for n in sacrifice_skills.split(",")]
        sacrificed = [s for s in skills if s.name in names_to_sacrifice]
        if not sacrificed:
            return json.dumps({"error": "No matching skills to sacrifice"}, indent=2)

        avg_level = sum(s.level for s in sacrificed) / len(sacrificed)
        combined_type = max(set(s.skill_type.value for s in sacrificed), key=lambda t: sum(1 for sk in sacrificed if sk.skill_type.value == t))

        new_skill_name = f"Mastered {'+'.join(s.name for s in sacrificed)}"
        new_skill = Skill(
            name=new_skill_name,
            skill_type=combined_type,
            level=int(avg_level) + 1,
            max_cooldown=max(s.max_cooldown for s in sacrificed),
            description=f"Evolved from sacrificing: {sacrifice_skills}",
        )

        skills = [s for s in skills if s.name not in names_to_sacrifice]
        skills.append(new_skill)
        return json.dumps({"new_skill": new_skill.model_dump(), "remaining_skills": [s.model_dump() for s in skills]}, indent=2)

    return json.dumps({"error": f"Unknown action: {action}"}, indent=2)


@tool
async def inventory_checker_and_updater(
    current_inventory_json: str,
    action: str = "check",
    item_name: str = "",
    quantity: int = 1,
    item_json: str = "",
    currency_amount: int = 0,
    currency_action: str = "",
) -> str:
    """Check and update character inventory, including currency control.

    Args:
        current_inventory_json: JSON string of current inventory items
        action: Action - 'check', 'add', 'remove', 'use', 'check_currency', 'spend_currency'
        item_name: Name of the item to check/use/remove
        quantity: Quantity for add/remove
        item_json: JSON string of item to add (for add action)
        currency_amount: Amount of currency
        currency_action: 'add' or 'spend'
    """
    try:
        inv_data = json.loads(current_inventory_json) if isinstance(current_inventory_json, str) else current_inventory_json
    except (json.JSONDecodeError, TypeError):
        inv_data = []

    inventory = [InventoryItem(**i) if isinstance(i, dict) else i for i in inv_data]

    if action == "check":
        item_found = None
        for item in inventory:
            if item.name.lower() == item_name.lower():
                item_found = item
                break
        if item_found:
            return json.dumps({
                "found": True,
                "item": item_found.model_dump() if hasattr(item_found, 'model_dump') else item_found,
                "quantity": item_found.quantity,
            }, indent=2)
        return json.dumps({"found": False, "message": f"Item '{item_name}' not in inventory"}, indent=2)

    elif action == "add":
        try:
            new_item_data = json.loads(item_json) if isinstance(item_json, str) else json.loads(item_json)
            existing = None
            for item in inventory:
                if item.name.lower() == new_item_data.get("name", "").lower():
                    existing = item
                    break
            if existing:
                existing.quantity += quantity
            else:
                new_item = InventoryItem(**new_item_data)
                new_item.quantity = quantity
                inventory.append(new_item)
            return json.dumps({
                "success": True,
                "inventory": [i.model_dump() if hasattr(i, 'model_dump') else i for i in inventory],
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to add item: {e}"}, indent=2)

    elif action == "remove":
        for item in inventory:
            if item.name.lower() == item_name.lower():
                if item.quantity < quantity:
                    return json.dumps({"error": f"Not enough '{item_name}': have {item.quantity}, need {quantity}"}, indent=2)
                item.quantity -= quantity
                if item.quantity <= 0:
                    inventory = [i for i in inventory if i.name.lower() != item_name.lower()]
                return json.dumps({
                    "success": True,
                    "removed": quantity,
                    "inventory": [i.model_dump() if hasattr(i, 'model_dump') else i for i in inventory],
                }, indent=2)
        return json.dumps({"error": f"Item '{item_name}' not found"}, indent=2)

    elif action == "check_currency":
        total_coins = sum(i.quantity for i in inventory if i.name.lower() in ["gold coin", "silver coin", "copper coin", "platinum coin"])
        return json.dumps({"total_currency": total_coins}, indent=2)

    elif action == "spend_currency":
        for item in inventory:
            if item.name.lower() in ["gold coin", "silver coin", "copper coin", "platinum coin"]:
                if item.quantity >= currency_amount:
                    item.quantity -= currency_amount
                    if item.quantity <= 0:
                        inventory = [i for i in inventory if i.name.lower() != item.name.lower()]
                    return json.dumps({"success": True, "spent": currency_amount}, indent=2)
                currency_amount -= item.quantity
                item.quantity = 0
                inventory = [i for i in inventory if i.quantity > 0]
        return json.dumps({"error": "Insufficient currency"}, indent=2)

    return json.dumps({"error": f"Unknown action: {action}"}, indent=2)


@tool
async def json_data_maker_and_tracker(
    action: str = "get",
    data_type: str = "",
    data_name: str = "",
    existing_data_json: str = "{}",
    new_data_json: str = "",
    relationship_entity: str = "",
    relationship_disposition: float = 0.0,
    relationship_description: str = "",
) -> str:
    """Track relationships, items, and game data in structured JSON format.

    Args:
        action: Action - 'get', 'set', 'update_relationship', 'list_all'
        data_type: Type of data (inventory, relationships, quests, locations, notes)
        data_name: Name/key of the specific data entry
        existing_data_json: JSON string of existing data store
        new_data_json: JSON string of new data to set
        relationship_entity: Entity name for relationship update
        relationship_disposition: Disposition value (-100 to 100)
        relationship_description: Description of the relationship
    """
    try:
        data_store = json.loads(existing_data_json) if isinstance(existing_data_json, str) else existing_data_json
    except (json.JSONDecodeError, TypeError):
        data_store = {}

    if data_type not in data_store:
        data_store[data_type] = {}

    if action == "get":
        entry = data_store.get(data_type, {}).get(data_name, None)
        return json.dumps({"data_type": data_type, "name": data_name, "data": entry}, indent=2)

    elif action == "set":
        try:
            new_data = json.loads(new_data_json) if isinstance(new_data_json, str) else new_data_json
            data_store[data_type][data_name] = new_data
            return json.dumps({"success": True, "data_type": data_type, "name": data_name, "data": new_data}, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to set data: {e}"}, indent=2)

    elif action == "update_relationship":
        if relationship_entity:
            rel = Relationship(
                entity_name=relationship_entity,
                disposition=relationship_disposition,
                description=relationship_description,
            )
            if "relationships" not in data_store:
                data_store["relationships"] = {}
            if relationship_entity in data_store["relationships"]:
                existing = data_store["relationships"][relationship_entity]
                new_disp = existing.get("disposition", 0) + relationship_disposition
                new_disp = max(-100, min(100, new_disp))
                rel.disposition = new_disp
            data_store["relationships"][relationship_entity] = rel.model_dump()
            return json.dumps({"success": True, "relationship": rel.model_dump()}, indent=2)
        return json.dumps({"error": "relationship_entity is required"}, indent=2)

    elif action == "list_all":
        return json.dumps(data_store, indent=2)

    return json.dumps({"error": f"Unknown action: {action}"}, indent=2)


@tool
async def use_skill(
    skill_name: str,
    current_stats_json: str = "{}",
    current_skills_json: str = "[]",
    target_json: str = "{}",
    modifier: int = 0,
    damage_multiplier: float = 1.0,
    mana: int = 50,
    max_mana: int = 100,
) -> str:
    """Execute a named skill with current character state and target context.
    Routes to the correct skill handler automatically.

    Args:
        skill_name: Name of the skill to use (e.g., 'slash', 'block', 'persuasion', 'fire_magic')
        current_stats_json: JSON string of current CharacterStats
        current_skills_json: JSON string of current skills list
        target_json: JSON string describing the target (enemy/item/NPC with type, defense, level, etc.)
        modifier: Flat modifier to the skill check roll
        damage_multiplier: Damage multiplier from plan quality, positioning, etc.
        mana: Current mana available
        max_mana: Maximum mana pool
    """
    from ...skills import SKILL_REGISTRY, get_skill, list_skills

    skill = get_skill(skill_name)
    if not skill:
        available = list_skills()
        return json.dumps({
            "error": f"Unknown skill: '{skill_name}'",
            "available_skills": available,
        }, indent=2)

    try:
        stats = json.loads(current_stats_json) if isinstance(current_stats_json, str) else current_stats_json
    except (json.JSONDecodeError, TypeError):
        stats = {}

    try:
        skills_data = json.loads(current_skills_json) if isinstance(current_skills_json, str) else current_skills_json
    except (json.JSONDecodeError, TypeError):
        skills_data = []

    try:
        target = json.loads(target_json) if isinstance(target_json, str) else target_json
    except (json.JSONDecodeError, TypeError):
        target = {}

    skill_level = 1
    for s in skills_data:
        if isinstance(s, dict):
            name = s.get("name", s.get("skill_name", "")).lower()
        else:
            name = str(s).lower()
        if name == skill_name.lower():
            skill_level = float(s.get("level", s.get("value", 1)))
            break

    handler = skill["handler"]
    stat_bonus = stats.get("level", 1) // 4 + stats.get("strength", 10) // 4

    ctx = {
        "skill_level": skill_level,
        "stat_bonus": stat_bonus,
        "modifier": modifier,
        "damage_multiplier": damage_multiplier,
        "target": target,
        "mana": mana,
        "max_mana": max_mana,
    }

    result = handler(ctx)
    result["skill_name"] = skill_name
    result["skill_category"] = skill.get("category", "")
    result["skill_level"] = skill_level

    return json.dumps(result, indent=2)
