from __future__ import annotations

from .base import make_result, success_check, xp_gain


def _lore(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    difficulty = target.get("obscurity", 10)
    diff = max(3, difficulty)
    check = success_check(lvl, diff, stat, 0)

    info = ""
    if check["success"]:
        info_depth = "basic"
        if lvl >= 5:
            info_depth = "detailed"
        if lvl >= 10:
            info_depth = "expert"
        if lvl >= 15:
            info_depth = "scholarly"
        info = f"{info_depth} knowledge about this subject"

    xp = xp_gain(lvl, difficulty / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"You recall {info}" if info else "You don't know anything about this",
        skill_xp=xp, cooldown=0,
        attributes={"info_depth": info},
    )


def _arcana(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    difficulty = target.get("magic_obscurity", 10)
    diff = max(3, difficulty)
    check = success_check(lvl, diff, stat, 0)

    info = ""
    if check["success"]:
        info_parts = ["magical properties"]
        if lvl >= 4:
            info_parts.append("origin")
        if lvl >= 7:
            info_parts.append("caster level estimate")
        if lvl >= 10:
            info_parts.append("weaknesses")
        info = ", ".join(info_parts)

    xp = xp_gain(lvl, difficulty / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Arcana reveals: {info}" if info else "The magic is inscrutable",
        skill_xp=xp, cooldown=0,
        attributes={"info": info},
    )


def _history(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    difficulty = target.get("age", 10)
    diff = max(3, difficulty)
    check = success_check(lvl, diff, stat, 0)

    era = ""
    if check["success"]:
        eras = ["recent", "century old", "ancient", "prehistoric", "mythical"]
        idx = min(len(eras) - 1, max(0, int(lvl * 0.3)))
        era = eras[idx]

    xp = xp_gain(lvl, difficulty / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"You recall {era} history about this" if era else "History is hazy on this point",
        skill_xp=xp, cooldown=0,
    )


def _medicine(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    wound_severity = target.get("wound_severity", 5)
    diff = max(3, wound_severity * 3)
    check = success_check(lvl, diff, stat, 0)

    healing = 0
    if check["success"]:
        healing = int(5 + lvl * 2 + stat)
        if check["quality"] == "critical":
            healing = int(healing * 1.5)

    xp = xp_gain(lvl, wound_severity / 5, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"You treat the wound for {healing} healing" if healing else "Your treatment fails",
        healing=healing, skill_xp=xp, cooldown=1,
        attributes={"healing": healing},
    )


def _healing(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mana = ctx.get("mana", 0)
    mana_cost = max(3, 8 - int(lvl * 0.3))

    if mana > 0 and mana < mana_cost:
        return make_result(False, f"Not enough mana ({mana}/{mana_cost})")

    diff = max(3, target.get("wound_severity", 5) * 2)
    check = success_check(lvl, diff, stat, 0)

    healing = 0
    if check["success"]:
        healing = int(10 + lvl * 3 + stat * 2)
        if check["quality"] == "critical":
            healing = int(healing * 2.0)

    xp = xp_gain(lvl, 1.3, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Healing restores {healing} HP" + (f" (mana -{mana_cost})" if mana > 0 else "") if healing else "Healing has no effect",
        healing=healing, skill_xp=xp, cooldown=2,
        attributes={"mana_cost": mana_cost if mana > 0 else 0},
    )


def _investigation(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    difficulty = target.get("hidden_dc", 10)
    diff = max(3, difficulty)
    check = success_check(lvl, diff, stat, 0)

    clues = []
    if check["success"]:
        possible = ["footprints", "documents", "hidden compartment", "traces of magic", "witness accounts", "physical evidence"]
        count = 1 + int(lvl * 0.4)
        clues = possible[:min(len(possible), count)]

    xp = xp_gain(lvl, difficulty / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"You discover: {', '.join(clues)}" if clues else "You find nothing suspicious",
        skill_xp=xp, cooldown=0,
        attributes={"clues_found": clues},
    )


SKILLS: dict[str, dict] = {
    "lore": {"handler": _lore, "category": "knowledge", "description": "Recall general knowledge and information"},
    "arcana": {"handler": _arcana, "category": "knowledge", "description": "Identify magic items, spells, and phenomena"},
    "history": {"handler": _history, "category": "knowledge", "description": "Recall historical events and figures"},
    "medicine": {"handler": _medicine, "category": "knowledge", "description": "Treat wounds and diagnose ailments"},
    "healing": {"handler": _healing, "category": "knowledge", "description": "Restore HP through magical or advanced healing"},
    "investigation": {"handler": _investigation, "category": "knowledge", "description": "Search for clues and hidden details"},
}
