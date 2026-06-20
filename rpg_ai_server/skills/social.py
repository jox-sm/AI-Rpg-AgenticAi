from __future__ import annotations

from .base import make_result, success_check, xp_gain


def _persuasion(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    mod = ctx.get("modifier", 0)

    diff = max(5, target.get("resolve", 10))
    check = success_check(lvl, diff, stat, mod, mastery_key="social")

    xp = xp_gain(lvl, 1.0, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="You successfully persuade them" if check["success"] else "They refuse to be persuaded",
        skill_xp=xp, cooldown=0,
        attributes={"margin": check["margin"]},
    )


def _diplomacy(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    current_relation = target.get("relationship", 0)

    diff = max(3, 10 - current_relation // 10)
    check = success_check(lvl, diff, stat, 0, mastery_key="social")

    relation_change = 0
    if check["success"]:
        base = 5 + int(lvl * 2)
        relation_change = base * (2 if check["quality"] == "critical" else (1.5 if check["quality"] == "good" else 1))
    else:
        relation_change = -3

    xp = xp_gain(lvl, 1.0, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Diplomacy changes relationship by {relation_change}",
        skill_xp=xp, cooldown=1,
        attributes={"relationship_delta": relation_change},
    )


def _intimidate(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    diff = max(5, target.get("level", 5) * 2 + target.get("resolve", 5))
    check = success_check(lvl, diff, stat, 0, mastery_key="social")

    xp = xp_gain(lvl, 1.2, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="They cower in fear!" if check["success"] else "They stand their ground",
        skill_xp=xp, cooldown=1,
        attributes={"intimidated": check["success"], "margin": check["margin"]},
    )


def _deceive(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    diff = max(5, target.get("perception", 10))
    check = success_check(lvl, diff, stat, 0, mastery_key="social")

    xp = xp_gain(lvl, 1.0, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect="They believe your lie" if check["success"] else "They see through your deception",
        skill_xp=xp, cooldown=0,
    )


def _bargain(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    base_price = ctx.get("base_price", 100)

    diff = max(5, target.get("mercantile", 10))
    check = success_check(lvl, diff, stat, 0, mastery_key="social")

    discount = 0
    if check["success"]:
        discount_pct = min(0.5, 0.1 + lvl * 0.02)
        if check["quality"] == "critical":
            discount_pct = min(0.7, discount_pct * 1.5)
        discount = int(base_price * discount_pct)

    xp = xp_gain(lvl, 1.0, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"You negotiate a {discount} discount (pay {base_price - discount})" if check["success"] else "The price stays firm",
        skill_xp=xp, cooldown=0,
        attributes={"discount": discount, "final_price": base_price - discount},
    )


SKILLS: dict[str, dict] = {
    "persuasion": {"handler": _persuasion, "category": "social", "description": "Convince others through charm and logic"},
    "diplomacy": {"handler": _diplomacy, "category": "social", "description": "Improve relationships and diffuse tension"},
    "intimidate": {"handler": _intimidate, "category": "social", "description": "Frighten or coerce through shows of force"},
    "deceive": {"handler": _deceive, "category": "social", "description": "Tell lies that hold up under scrutiny"},
    "bargain": {"handler": _bargain, "category": "social", "description": "Haggle for better prices on goods"},
}
