from __future__ import annotations

import random

from .base import make_result, success_check, xp_gain


def _tracking(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    difficulty = target.get("track_difficulty", 10)
    diff = max(3, difficulty - int(lvl * 0.5))
    check = success_check(lvl, diff, stat, 0, mastery_key="survival")

    info = ""
    if check["success"]:
        info_pieces = []
        if lvl >= 3:
            info_pieces.append("species")
        if lvl >= 5:
            info_pieces.append("health estimate")
        if lvl >= 8:
            info_pieces.append("how long ago they passed")
        if lvl >= 12:
            info_pieces.append("exact number in group")
        info = ", ".join(info_pieces) if info_pieces else "faint trail"

    xp = xp_gain(lvl, 1.0, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"You find tracks and learn: {info}" if check["success"] else "The trail goes cold",
        skill_xp=xp, cooldown=0,
        attributes={"info_found": info},
    )


def _hunting(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    prey_size = ctx.get("prey_size", "small")

    size_mod = {"small": 5, "medium": 10, "large": 15, "massive": 22}
    diff = 5 + size_mod.get(prey_size, 10)
    check = success_check(lvl, diff, stat, 0, mastery_key="survival")

    harvest = ""
    meat = 0
    if check["success"]:
        meat = int(5 + lvl * 2 + random.randint(1, 10))
        harvest = f"{meat} units of meat"
        if check["quality"] == "critical":
            harvest += " + rare trophy"

    xp = xp_gain(lvl, 1.1, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Successful hunt! You harvest {harvest}" if check["success"] else "The prey escapes",
        skill_xp=xp, cooldown=2,
        attributes={"meat": meat, "prey_size": prey_size},
    )


def _foraging(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    biome = ctx.get("biome", "forest")

    biomes = {"forest": 8, "mountain": 12, "desert": 15, "swamp": 6, "plains": 10}
    diff = biomes.get(biome, 10)
    check = success_check(lvl, diff, stat, 0, mastery_key="survival")

    found = []
    if check["success"]:
        count = 1 + int(lvl * 0.5) + random.randint(0, 2)
        items = ["herbs", "mushrooms", "berries", "roots", "wild greens", "medicinal plants"]
        found = random.sample(items, min(count, len(items)))

    xp = xp_gain(lvl, 0.8, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Found: {', '.join(found)}" if found else "You find nothing useful",
        skill_xp=xp, cooldown=1,
        attributes={"items_found": found, "biome": biome},
    )


def _skinning(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    stat = ctx.get("stat_bonus", 0)
    creature_type = ctx.get("creature_type", "beast")

    diff = 5 + {"beast": 0, "monster": 5, "dragon": 15, "magical": 10}.get(creature_type, 5)
    check = success_check(lvl, diff, stat, 0, mastery_key="survival")

    materials = {}
    if check["success"]:
        quality = "rough" if lvl < 3 else ("standard" if lvl < 7 else ("fine" if lvl < 12 else "masterwork"))
        materials = {"hide": quality, "bones": int(lvl * 0.5 + 2)}
        if check["quality"] == "critical":
            materials["rare_part"] = True

    xp = xp_gain(lvl, 1.2, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Skinned cleanly — {quality} hide, {materials.get('bones', 0)} bones" + (" + rare part!" if materials.get("rare_part") else "") if check["success"] else "You damage the pelt, ruining it",
        skill_xp=xp, cooldown=1,
        attributes={"materials": materials},
    )


SKILLS: dict[str, dict] = {
    "tracking": {"handler": _tracking, "category": "survival", "description": "Follow and interpret tracks and signs"},
    "hunting": {"handler": _hunting, "category": "survival", "description": "Hunt game for food and materials"},
    "foraging": {"handler": _foraging, "category": "survival", "description": "Gather wild plants and resources"},
    "skinning": {"handler": _skinning, "category": "survival", "description": "Harvest hides and materials from slain creatures"},
}
