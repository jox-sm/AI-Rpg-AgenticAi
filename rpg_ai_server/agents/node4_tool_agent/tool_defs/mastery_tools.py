from __future__ import annotations

import json

from langchain_core.tools import tool


@tool
async def craft_with_choice(
    skill_name: str,
    player_location: str = "unknown",
    worker_id: str = "",
    current_stats_json: str = "{}",
    current_skills_json: str = "[]",
    target_json: str = "{}",
    gold: int = 0,
    modifier: int = 0,
    damage_multiplier: float = 1.0,
    mana: int = 50,
    max_mana: int = 100,
) -> str:
    """Craft an item with location-aware worker choice.
    If workers are available at your location for this skill,
    you'll be offered the choice to hire them (uses their mastery, costs gold)
    or do it yourself (uses your own mastery, free).

    Args:
        skill_name: Crafting skill (smithing, alchemy, woodworking, enchanting)
        player_location: Where the player currently is (e.g., 'town_forge', 'blacksmith_district')
        worker_id: If set, skip choice and directly hire this worker
        current_stats_json: JSON string of current CharacterStats
        current_skills_json: JSON string of current skills list
        target_json: JSON string describing what to craft (item_rarity, potion_tier, etc.)
        gold: Player's current gold for cost calculation
        modifier: Flat modifier to the attempt
        damage_multiplier: Damage multiplier (for weapon crafting)
        mana: Current mana (for enchanting)
        max_mana: Maximum mana pool
    """
    from ....skills import get_skill
    from ....skills.crafting import check_worker_availability, _SKILL_TO_MASTERY, _SKILL_TO_STATION
    from ....utils.worker_manager import (
        calculate_worker_cost,
        can_afford_worker,
        find_workers_at_location,
        format_worker_option,
    )

    skill = get_skill(skill_name)
    if not skill:
        return json.dumps({"error": f"Unknown skill: '{skill_name}'"}, indent=2)

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

    stat_bonus = stats.get("level", 1) // 4 + stats.get("strength", 10) // 4
    mastery_key = _SKILL_TO_MASTERY.get(skill_name, skill_name)

    availability = check_worker_availability(skill_name, player_location, int(skill_level))
    workers = availability.get("workers", [])

    if worker_id:
        matched = [w for w in workers if w["id"] == worker_id]
        if not matched:
            all_workers = find_workers_at_location(player_location)
            matched = [w for w in all_workers if w["id"] == worker_id]
        if not matched:
            return json.dumps({
                "error": f"Worker '{worker_id}' not found at '{player_location}'",
                "available_workers": [w["id"] for w in workers],
            }, indent=2)

        worker = matched[0]
        difficulty = _resolve_difficulty(target, skill_name)
        cost = calculate_worker_cost(worker, difficulty)

        if not can_afford_worker(gold, cost):
            return json.dumps({
                "error": f"Not enough gold! Need {cost}, have {gold}",
                "worker": worker["name"],
                "cost": cost,
                "gold": gold,
            }, indent=2)

        ctx = {
            "skill_level": skill_level,
            "stat_bonus": stat_bonus,
            "modifier": modifier,
            "damage_multiplier": damage_multiplier,
            "target": target,
            "mana": mana,
            "max_mana": max_mana,
            "worker_id": worker_id,
        }
        for key in ("item_rarity", "potion_tier", "complexity", "enchant_power"):
            if key in target:
                ctx[key] = target[key]

        handler = skill["handler"]
        result = handler(ctx)
        result["skill_name"] = skill_name
        result["skill_category"] = skill.get("category", "")
        result["skill_level"] = skill_level
        result["worker_hired"] = worker["name"]
        result["gold_cost"] = cost
        result["gold_remaining"] = gold - cost

        return json.dumps(result, indent=2)

    if availability["workers_available"]:
        choice_info = {
            "workers_available": True,
            "station": availability.get("station", ""),
            "player_location": player_location,
            "player_mastery_level": int(skill_level),
            "workers": workers,
            "instruction": (
                f"You are at {player_location} near a {availability.get('station', 'workstation')}. "
                f"Your {skill_name} mastery: Lv{int(skill_level)}. "
                "You can hire a worker or craft it yourself. "
                "To hire: call craft_with_choice with the worker_id. "
                "To do it yourself: call craft_with_choice with worker_id='' or use use_skill directly."
            ),
        }
        return json.dumps(choice_info, indent=2)

    ctx = {
        "skill_level": skill_level,
        "stat_bonus": stat_bonus,
        "modifier": modifier,
        "damage_multiplier": damage_multiplier,
        "target": target,
        "mana": mana,
        "max_mana": max_mana,
    }
    for key in ("item_rarity", "potion_tier", "complexity", "enchant_power"):
        if key in target:
            ctx[key] = target[key]

    handler = skill["handler"]
    result = handler(ctx)
    result["skill_name"] = skill_name
    result["skill_category"] = skill.get("category", "")
    result["skill_level"] = skill_level
    result["crafted_by"] = "player"

    return json.dumps(result, indent=2)


@tool
async def list_available_workers(
    player_location: str = "unknown",
    skill_name: str = "",
) -> str:
    """List NPC workers available at the player's current location.

    Args:
        player_location: Where the player currently is
        skill_name: Optional filter — only show workers with this skill
    """
    from ....utils.worker_manager import (
        find_workers_at_location,
        find_workers_for_skill,
        get_all_workers,
    )

    if skill_name:
        from ....skills.crafting import _SKILL_TO_MASTERY
        mastery_key = _SKILL_TO_MASTERY.get(skill_name, skill_name)
        raw = find_workers_for_skill(mastery_key)
        at_location = find_workers_at_location(player_location)
        workers = [w for w in raw if w in at_location]
    else:
        workers = find_workers_at_location(player_location)

    if not workers:
        return json.dumps({
            "location": player_location,
            "workers_available": False,
            "message": f"No workers found at '{player_location}'",
        }, indent=2)

    result = {
        "location": player_location,
        "workers_available": True,
        "worker_count": len(workers),
        "workers": [
            {
                "id": w["id"],
                "name": w["name"],
                "title": w.get("title", ""),
                "station": w.get("station", ""),
                "mastery": w.get("mastery", {}),
                "cost_per_attempt": w.get("cost_per_attempt", 0),
                "currency": w.get("currency", "gold"),
                "description": w.get("description", ""),
            }
            for w in workers
        ],
    }
    return json.dumps(result, indent=2)


@tool
async def check_mastery(
    skill_name: str = "",
    current_skills_json: str = "[]",
) -> str:
    """Check mastery levels and success rate tables.

    Args:
        skill_name: Optional — specific skill to check (smithing, magic, combat_offense, etc.)
        current_skills_json: JSON string of current skills list
    """
    from ....utils.mastery import get_mastery_skills, mastery_table, base_success_rate
    from ....utils.worker_manager import find_workers_for_skill

    try:
        skills_data = json.loads(current_skills_json) if isinstance(current_skills_json, str) else current_skills_json
    except (json.JSONDecodeError, TypeError):
        skills_data = []

    player_skills = {}
    for s in skills_data:
        if isinstance(s, dict):
            player_skills[s.get("name", "").lower()] = float(s.get("level", s.get("value", 1)))
        else:
            player_skills[str(s).lower()] = 1

    if skill_name:
        from ....skills.crafting import _SKILL_TO_MASTERY
        mastery_key = _SKILL_TO_MASTERY.get(skill_name, skill_name)
        tbl = mastery_table(mastery_key, max_level=20)
        player_lv = int(player_skills.get(skill_name.lower(), player_skills.get(mastery_key, 1)))
        workers = find_workers_for_skill(mastery_key)

        worker_info = []
        for w in workers:
            wlvl = 0
            for k, v in w.get("mastery", {}).items():
                if k.lower().strip() == mastery_key.lower().strip():
                    wlvl = int(v)
                    break
            worker_info.append({
                "id": w["id"],
                "name": w["name"],
                "mastery_level": wlvl,
                "cost": w.get("cost_per_attempt", 0),
                "location": w.get("locations", [])[:2],
            })

        return json.dumps({
            "skill": mastery_key,
            "player_level": player_lv,
            "player_rate_at_current_level": round(base_success_rate(player_lv, mastery_key) * 100, 1),
            "mastery_table": tbl,
            "available_workers": worker_info,
        }, indent=2)

    all_skills = get_mastery_skills()
    result = []
    for s in all_skills:
        key = s["key"]
        lv = int(player_skills.get(key, 1))
        result.append({
            "skill": key,
            "label": s["label"],
            "player_level": lv,
            "player_rate": round(base_success_rate(lv, key) * 100, 1),
        })

    return json.dumps({"skills": result}, indent=2)


def _resolve_difficulty(target: dict, skill_name: str) -> str:
    diff_map = {1: "trivial", 2: "easy", 3: "normal", 4: "hard", 5: "very_hard", 6: "legendary"}
    if skill_name == "smithing":
        return diff_map.get(target.get("item_rarity", 1), "normal")
    if skill_name == "alchemy":
        return diff_map.get(target.get("potion_tier", 1), "normal")
    if skill_name == "woodworking":
        return diff_map.get(target.get("complexity", 1), "normal")
    if skill_name == "enchanting":
        return diff_map.get(target.get("enchant_power", 1), "normal")
    return "normal"
