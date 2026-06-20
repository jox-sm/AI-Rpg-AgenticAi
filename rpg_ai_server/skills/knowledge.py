from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from ..utils.items_db import ItemsDB
from .base import make_result, success_check, xp_gain

_ITEMS_DB = ItemsDB()
_RECIPES: list[dict] | None = None


def _load_recipes() -> list[dict]:
    global _RECIPES
    if _RECIPES is None:
        path = Path(_ITEMS_DB.data_dir) / "recipes.json"
        if path.exists():
            _RECIPES = json.loads(path.read_text(encoding="utf-8"))
        else:
            _RECIPES = []
    return _RECIPES


def _lore(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    difficulty = target.get("obscurity", 10)
    diff = max(3, difficulty)
    check = success_check(lvl, diff, stat, 0, mastery_key="knowledge")

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

    item_name = target.get("name", target.get("item_name", ""))
    difficulty = target.get("magic_obscurity", 10)
    diff = max(3, difficulty)
    check = success_check(lvl, diff, stat, 0, mastery_key="knowledge")

    info = ""
    db_match = None
    if item_name:
        db_match = _ITEMS_DB.get_by_name(item_name)
        if not db_match:
            db_match = _ITEMS_DB.search(item_name, limit=3)

    if check["success"]:
        info_parts = ["magical properties"]
        if lvl >= 4:
            info_parts.append("origin")
        if lvl >= 7:
            info_parts.append("caster level estimate")
        if lvl >= 10:
            info_parts.append("weaknesses")
        info = ", ".join(info_parts)
        if db_match:
            if isinstance(db_match, list):
                info += f" — matched {len(db_match)} items in database"
            else:
                info += f" — identified as {db_match.get('name', 'unknown')}"

    xp = xp_gain(lvl, difficulty / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"Arcana reveals: {info}" if info else "The magic is inscrutable",
        skill_xp=xp, cooldown=0,
        attributes={"info": info, "db_item": db_match if isinstance(db_match, dict) else None},
    )


def _history(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)

    difficulty = target.get("age", 10)
    diff = max(3, difficulty)
    check = success_check(lvl, diff, stat, 0, mastery_key="knowledge")

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
    check = success_check(lvl, diff, stat, 0, mastery_key="knowledge")

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
    check = success_check(lvl, diff, stat, 0, mastery_key="knowledge")

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
    query = target.get("search_query", target.get("name", target.get("item_name", "")))

    difficulty = target.get("hidden_dc", 10)
    diff = max(3, difficulty)
    check = success_check(lvl, diff, stat, 0, mastery_key="knowledge")

    clues = []
    db_results = []
    if check["success"]:
        possible = ["footprints", "documents", "hidden compartment", "traces of magic", "witness accounts", "physical evidence"]
        count = 1 + int(lvl * 0.4)
        clues = possible[:min(len(possible), count)]

        if query:
            db_results = _ITEMS_DB.search(query, limit=count)
            if db_results:
                item_names = [i.get("name", "unknown") for i in db_results]
                clues.append(f"items found: {', '.join(item_names)}")

    xp = xp_gain(lvl, difficulty / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=f"You discover: {', '.join(clues)}" if clues else "You find nothing suspicious",
        skill_xp=xp, cooldown=0,
        attributes={"clues_found": clues, "db_items_found": db_results},
    )


_WORD_RE = re.compile(r"[a-zA-Z0-9]+")


def _bow_tokens(text: str) -> set[str]:
    return {m.group().lower() for m in _WORD_RE.finditer(text) if len(m.group()) > 1}


def _bow_score(query_tokens: set[str], recipe_tokens: set[str]) -> float:
    if not query_tokens:
        return 0.0
    return len(query_tokens & recipe_tokens) / len(query_tokens)


def _char_bigrams(text: str, pad: int = 2) -> Counter:
    padded = "#" * pad + text.lower() + "#" * pad
    return Counter(padded[i:i+2] for i in range(len(padded) - 1))


def _cosine_sim(a: Counter, b: Counter) -> float:
    num = sum((a & b).values())
    den = (sum(a.values()) ** 0.5) * (sum(b.values()) ** 0.5)
    return num / den if den else 0.0


def _recipes(ctx: dict) -> dict:
    lvl = ctx.get("skill_level", 1)
    target = ctx.get("target", {})
    stat = ctx.get("stat_bonus", 0)
    query = target.get("query", target.get("name", target.get("item_name", "")))

    difficulty = target.get("recipe_dc", 10)
    diff = max(3, difficulty)
    check = success_check(lvl, diff, stat, 0, mastery_key="knowledge")

    results = []
    if query and check["success"]:
        q_tokens = _bow_tokens(query)
        # Extend query tokens with items-db cross-refs (_src_id, category)
        db_item = _ITEMS_DB.get_by_name(query)
        if db_item:
            src = db_item.get("_src_id") or ""
            if src:
                q_tokens.update(_bow_tokens(src))
            cat = db_item.get("Category") or db_item.get("category") or ""
            if cat:
                q_tokens.update(_bow_tokens(cat))
        else:
            for item in _ITEMS_DB.search(query, limit=3):
                src = item.get("_src_id") or ""
                if src:
                    q_tokens.update(_bow_tokens(src))

        if not q_tokens:
            q_tokens = {query.lower()}

        recipes = _load_recipes()
        scored: list[tuple[float, dict]] = []
        seen: set[str] = set()
        for r in recipes:
            combined = " ".join([
                r.get("name", ""),
                r.get("Station", ""),
                r.get("Required Skill", ""),
                r.get("Ingredients", ""),
                r.get("Result", ""),
            ])
            r_tokens = _bow_tokens(combined)
            score = _bow_score(q_tokens, r_tokens)
            if score > 0:
                rid = r.get("_src_id", str(r.get("id", "")))
                if rid not in seen:
                    seen.add(rid)
                    scored.append((score, r))

        if not scored:
            for item in _ITEMS_DB.search(query, limit=5):
                name = item.get("name", "")
                src = item.get("_src_id") or ""
                if name:
                    q_tokens = _bow_tokens(name)
                    if src:
                        q_tokens.update(_bow_tokens(src))
                    for r in recipes:
                        combined = " ".join([
                            r.get("name", ""),
                            r.get("Station", ""),
                            r.get("Required Skill", ""),
                            r.get("Ingredients", ""),
                            r.get("Result", ""),
                        ])
                        r_tokens = _bow_tokens(combined)
                        score = _bow_score(q_tokens, r_tokens)
                        if score > 0:
                            rid = r.get("_src_id", str(r.get("id", "")))
                            if rid not in seen:
                                seen.add(rid)
                                scored.append((score * 0.95, r))

        if scored:
            scored.sort(key=lambda x: -x[0])

        results = [_format_recipe(r) for _, r in scored]

    count = max(1, min(8, int(lvl * 0.3)))
    if len(results) > count:
        results = results[:count]

    result_str = ""
    if results:
        lines = []
        for r in results:
            lines.append(f"  {r['name']} @ {r['station']} ({r['skill_required']} Lv{r['skill_level']})")
            lines.append(f"    Ingredients: {r['ingredients']}")
            lines.append(f"    Result: {r['result']} | Time: {r['crafting_time']} | Success: {r['success_rate']}")
        result_str = "\n".join(lines)

    xp = xp_gain(lvl, difficulty / 10, check["success"], check["quality"])
    return make_result(
        success=check["success"],
        effect=result_str if result_str else "You don't know any recipes matching that",
        skill_xp=xp, cooldown=0,
        attributes={"recipes_found": results, "recipe_count": len(results)},
   )


def _format_recipe(r: dict) -> dict:
    return {
        "name": r.get("name", ""),
        "station": r.get("Station", ""),
        "skill_required": r.get("Required Skill", ""),
        "skill_level": r.get("Skill Level", ""),
        "ingredients": r.get("Ingredients", ""),
        "result": r.get("Result", ""),
        "crafting_time": r.get("Crafting Time", ""),
        "success_rate": r.get("Success Rate", ""),
    }


SKILLS: dict[str, dict] = {
    "lore": {"handler": _lore, "category": "knowledge", "description": "Recall general knowledge and information"},
    "arcana": {"handler": _arcana, "category": "knowledge", "description": "Identify magic items, spells, and phenomena"},
    "history": {"handler": _history, "category": "knowledge", "description": "Recall historical events and figures"},
    "medicine": {"handler": _medicine, "category": "knowledge", "description": "Treat wounds and diagnose ailments"},
    "healing": {"handler": _healing, "category": "knowledge", "description": "Restore HP through magical or advanced healing"},
    "investigation": {"handler": _investigation, "category": "knowledge", "description": "Search for clues and hidden details"},
    "recipes": {"handler": _recipes, "category": "knowledge", "description": "Look up crafting recipes — query by item, ingredient, station, or skill"},
}
