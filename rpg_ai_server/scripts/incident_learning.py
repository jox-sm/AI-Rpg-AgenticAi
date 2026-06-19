from __future__ import annotations

import json
import math
import random
from typing import Any, Optional

ACTION_CATEGORIES: dict[str, dict] = {
    "combat_training": {
        "primary_stat": "strength",
        "secondary_stat": "stamina",
        "stat_mult": 1.0,
        "stamina_mult": 1.5,
        "skills": [
            {"name": "melee", "mult": 1.2},
        ],
        "keywords": [
            "train sword", "practice sword", "spar", "drill", "train blade",
            "train axe", "train mace", "combat training", "weapon practice",
            "fight dummy", "training dummy", "practice striking",
        ],
        "description": "Physical weapon training",
    },
    "slashing_training": {
        "primary_stat": "strength",
        "secondary_stat": "stamina",
        "stat_mult": 1.2,
        "stamina_mult": 1.3,
        "skills": [
            {"name": "melee", "mult": 1.3},
            {"name": "slashing", "mult": 2.0},
            {"name": "sword_mastery", "mult": 1.8},
        ],
        "keywords": [
            "train slashing", "practice slash", "sword drill", "cut practice",
            "train sword", "practice sword", "blade training", "sword forms",
            "sword technique", "train with sword",
        ],
        "description": "Sword and slashing weapon training",
    },
    "piercing_training": {
        "primary_stat": "dexterity",
        "secondary_stat": "strength",
        "stat_mult": 1.2,
        "stamina_mult": 1.0,
        "skills": [
            {"name": "melee", "mult": 1.2},
            {"name": "piercing", "mult": 2.0},
            {"name": "spear_mastery", "mult": 1.8},
        ],
        "keywords": [
            "train spear", "practice thrust", "spear drill", "train rapier",
            "practice piercing", "piercing training", "train lance",
        ],
        "description": "Spear and piercing weapon training",
    },
    "bludgeoning_training": {
        "primary_stat": "strength",
        "secondary_stat": "stamina",
        "stat_mult": 1.3,
        "stamina_mult": 1.5,
        "skills": [
            {"name": "melee", "mult": 1.1},
            {"name": "bludgeoning", "mult": 2.0},
            {"name": "hammer_mastery", "mult": 1.8},
        ],
        "keywords": [
            "train hammer", "practice mace", "bludgeon drill", "train maul",
            "practice bludgeoning", "bludgeoning training", "heavy weapon training",
        ],
        "description": "Blunt weapon training",
    },
    "archery_training": {
        "primary_stat": "dexterity",
        "secondary_stat": "perception",
        "stat_mult": 1.2,
        "stamina_mult": 0.7,
        "skills": [
            {"name": "ranged", "mult": 2.0},
            {"name": "archery", "mult": 1.8},
        ],
        "keywords": [
            "train bow", "practice archery", "shoot arrow", "target practice",
            "train crossbow", "ranged practice", "archery training",
        ],
        "description": "Ranged weapon training",
    },
    "strategic_planning": {
        "primary_stat": "wisdom",
        "secondary_stat": "intelligence",
        "stat_mult": 1.5,
        "stamina_mult": 0.0,
        "skills": [
            {"name": "tactics", "mult": 2.0},
            {"name": "strategy", "mult": 1.5},
        ],
        "keywords": [
            "plan", "strategy", "tactical", "outsmart", "clever plan",
            "brilliant idea", "figure out", "solve", "puzzle", "scheme",
            "master plan", "cunning", "trap", "ambush",
        ],
        "description": "Strategic thinking and planning",
    },
    "physical_training": {
        "primary_stat": "strength",
        "secondary_stat": "stamina",
        "stat_mult": 1.0,
        "stamina_mult": 2.0,
        "skills": [
            {"name": "athletics", "mult": 1.5},
            {"name": "endurance", "mult": 1.2},
        ],
        "keywords": [
            "gym", "exercise", "push up", "pull up", "lift", "workout",
            "train body", "physical training", "run", "sprint", "jog",
            "calisthenics", "weight lift", "strength train",
        ],
        "description": "General physical conditioning",
    },
    "agility_training": {
        "primary_stat": "dexterity",
        "secondary_stat": "stamina",
        "stat_mult": 1.3,
        "stamina_mult": 1.0,
        "skills": [
            {"name": "acrobatics", "mult": 2.0},
            {"name": "reflexes", "mult": 1.3},
        ],
        "keywords": [
            "train agility", "parkour", "dodge practice", "balance training",
            "acrobatics", "gymnastics", "flexibility", "stretch",
        ],
        "description": "Agility and reflexes training",
    },
    "study": {
        "primary_stat": "intelligence",
        "secondary_stat": "wisdom",
        "stat_mult": 1.5,
        "stamina_mult": 0.0,
        "skills": [
            {"name": "lore", "mult": 1.8},
            {"name": "arcana", "mult": 1.5},
            {"name": "history", "mult": 1.2},
        ],
        "keywords": [
            "study", "read", "research", "learn", "book", "library",
            "study magic", "study lore", "research monster", "examine",
            "investigate", "analyze", "scroll",
        ],
        "description": "Studying and research",
    },
    "magic_practice": {
        "primary_stat": "intelligence",
        "secondary_stat": "wisdom",
        "stat_mult": 1.2,
        "stamina_mult": 0.0,
        "skills": [
            {"name": "spellcasting", "mult": 2.0},
            {"name": "mana_control", "mult": 1.5},
        ],
        "keywords": [
            "practice magic", "train spell", "meditate", "channel mana",
            "spell practice", "magic training", "train sorcery",
            "practice enchant", "cast spell repeatedly",
        ],
        "description": "Magic and spellcasting practice",
    },
    "crafting": {
        "primary_stat": "dexterity",
        "secondary_stat": "intelligence",
        "stat_mult": 1.0,
        "stamina_mult": 0.0,
        "skills": [
            {"name": "crafting", "mult": 2.0},
            {"name": "smithing", "mult": 1.5},
        ],
        "keywords": [
            "craft", "smith", "forge", "brew", "cook", "alchemy",
            "build", "construct", "repair", "make", "create item",
            "tinker", "blacksmith", "woodwork",
        ],
        "description": "Crafting and item creation",
    },
    "social": {
        "primary_stat": "charisma",
        "secondary_stat": "wisdom",
        "stat_mult": 1.5,
        "stamina_mult": 0.0,
        "skills": [
            {"name": "persuasion", "mult": 2.0},
            {"name": "diplomacy", "mult": 1.3},
        ],
        "keywords": [
            "negotiate", "persuade", "charm", "convince", "bargain",
            "befriend", "diplomacy", "talk", "debate", "speech",
            "intimidate", "deceive",
        ],
        "description": "Social interaction and persuasion",
    },
    "stealth_practice": {
        "primary_stat": "dexterity",
        "secondary_stat": "perception",
        "stat_mult": 1.2,
        "stamina_mult": 0.0,
        "skills": [
            {"name": "stealth", "mult": 2.0},
            {"name": "sleight_of_hand", "mult": 1.3},
        ],
        "keywords": [
            "sneak", "hide", "stealth", "pickpocket", "lockpick",
            "move silently", "shadow", "conceal", "ambush setup",
            "stealth practice",
        ],
        "description": "Stealth and subterfuge training",
    },
    "survival": {
        "primary_stat": "constitution",
        "secondary_stat": "wisdom",
        "stat_mult": 1.2,
        "stamina_mult": 1.0,
        "skills": [
            {"name": "survival", "mult": 2.0},
            {"name": "tracking", "mult": 1.3},
        ],
        "keywords": [
            "hunt", "forage", "track", "camp", "survive", "navigate",
            "wilderness", "explore forest", "gather herb", "set trap",
            "fish", "skin", "butcher",
        ],
        "description": "Wilderness survival and hunting",
    },
    "defense_training": {
        "primary_stat": "constitution",
        "secondary_stat": "stamina",
        "stat_mult": 1.3,
        "stamina_mult": 1.5,
        "skills": [
            {"name": "block", "mult": 2.0},
            {"name": "endurance", "mult": 1.5},
        ],
        "keywords": [
            "train defense", "practice block", "shield training", "guard practice",
            "parry training", "defensive drill", "practice dodge",
        ],
        "description": "Defensive and blocking training",
    },
    "healing_practice": {
        "primary_stat": "wisdom",
        "secondary_stat": "intelligence",
        "stat_mult": 1.2,
        "stamina_mult": 0.0,
        "skills": [
            {"name": "healing", "mult": 2.0},
            {"name": "medicine", "mult": 1.5},
        ],
        "keywords": [
            "heal", "treat wound", "bandage", "medicine", "first aid",
            "practice healing", "herbalism", "tend", "cure", "restore",
        ],
        "description": "Healing and medicine practice",
    },
}


def classify_action(action_description: str) -> list[dict]:
    desc = action_description.lower()
    matches: list[tuple[int, str]] = []

    for cat_name, cat in ACTION_CATEGORIES.items():
        score = 0
        for kw in cat["keywords"]:
            if kw in desc:
                score += 1
        keyword_overlap = sum(1 for kw in cat["keywords"] if kw in desc)
        if keyword_overlap > 0:
            score += keyword_overlap * 2

        action_words = desc.split()
        cat_words = cat["description"].lower().split()
        word_overlap = len(set(action_words) & set(cat_words))
        score += word_overlap

        if score > 0:
            matches.append((score, cat_name))

    matches.sort(key=lambda x: -x[0])
    threshold = max(1, matches[0][0] * 0.5) if matches else 0

    results = []
    seen = set()
    for score, name in matches:
        if name not in seen and score >= threshold:
            results.append({"category": name, "confidence": round(score / max(matches[0][0], 1), 2), **ACTION_CATEGORIES[name]})
            seen.add(name)

    return results


DIMINISHING_RETURNS_CAP = 50


def _gain(stat_value: int, base_gain: float, mult: float = 1.0, intensity: float = 1.0) -> float:
    dim = 1.0 - (min(stat_value, DIMINISHING_RETURNS_CAP) / DIMINISHING_RETURNS_CAP) * 0.7
    raw = base_gain * mult * intensity * dim
    variance = random.uniform(0.8, 1.2)
    return round(raw * variance, 2)


def process_incidents(
    current_stats: dict[str, Any],
    current_skills: Optional[list[dict[str, Any]]] = None,
    incidents: Optional[list[dict[str, Any]]] = None,
    base_stat_gain: float = 0.3,
    base_skill_gain: float = 0.5,
) -> dict:
    stats = dict(current_stats)
    skill_list = list(current_skills or [])
    incidents = incidents or []

    default_skill_scores: dict[str, float] = {}
    for s in skill_list:
        name = s.get("name", s.get("skill_name", "")).lower()
        default_skill_scores[name] = float(s.get("level", s.get("value", 1)))

    total_stat_gains: dict[str, float] = {}
    total_skill_gains: dict[str, float] = {}
    action_log: list[str] = []

    for incident in incidents:
        if isinstance(incident, str):
            desc = incident
            intensity = 1.0
        else:
            desc = incident.get("description", incident.get("action", ""))
            intensity = float(incident.get("intensity", incident.get("quality", 1.0)))

        categories = classify_action(desc)
        if not categories:
            action_log.append(f"No matching category for: {desc[:50]}...")
            continue

        cat = categories[0]
        cat_name = cat["category"]
        cat_data = ACTION_CATEGORIES[cat_name]

        primary = cat_data["primary_stat"]
        secondary = cat_data["secondary_stat"]
        stamina_mult = cat_data["stamina_mult"]

        if primary not in total_stat_gains:
            total_stat_gains[primary] = 0.0
        if secondary not in total_stat_gains:
            total_stat_gains[secondary] = 0.0

        current_primary = stats.get(primary, 10)
        current_secondary = stats.get(secondary, 10)

        primary_gain = _gain(current_primary, base_stat_gain, cat_data["stat_mult"], intensity)
        secondary_gain = _gain(current_secondary, base_stat_gain * 0.6, cat_data["stat_mult"], intensity)

        total_stat_gains[primary] += primary_gain
        total_stat_gains[secondary] += secondary_gain

        stamina_gain = 0.0
        if stamina_mult > 0:
            current_stamina = stats.get("stamina", 10)
            stamina_gain = _gain(current_stamina, base_stat_gain * 0.5, stamina_mult, intensity)
            total_stat_gains["stamina"] = total_stat_gains.get("stamina", 0.0) + stamina_gain

        skill_gains_local: list[str] = []
        for skill_def in cat_data["skills"]:
            sname = skill_def["name"]
            current_val = default_skill_scores.get(sname, 1)
            gain = _gain(int(current_val * 10), base_skill_gain, skill_def["mult"], intensity)
            total_skill_gains[sname] = total_skill_gains.get(sname, 0.0) + gain
            skill_gains_local.append(f"{sname}+{round(gain, 2)}")

        action_log.append(
            f"{cat_name}: {primary}+{round(primary_gain, 2)}, {secondary}+{round(secondary_gain, 2)}"
            + (f", stamina+{round(stamina_gain, 2)}" if stamina_gain > 0 else "")
            + (f", [{', '.join(skill_gains_local)}]" if skill_gains_local else "")
        )

    for stat_name, gain in total_stat_gains.items():
        current = stats.get(stat_name, 10)
        stats[stat_name] = round(current + gain, 1)

    updated_skills = list(skill_list)
    for sname, gain in total_skill_gains.items():
        found = False
        for s in updated_skills:
            name = s.get("name", s.get("skill_name", "")).lower()
            if name == sname:
                current_val = float(s.get("level", s.get("value", 1)))
                s["level"] = round(current_val + gain, 2)
                s["value"] = s["level"]
                found = True
                break
        if not found:
            updated_skills.append({
                "name": sname,
                "skill_name": sname,
                "level": round(1 + gain, 2),
                "value": round(1 + gain, 2),
                "source": "incident_learning",
            })

    return {
        "updated_stats": stats,
        "updated_skills": updated_skills,
        "stat_gains": {k: round(v, 2) for k, v in total_stat_gains.items()},
        "skill_gains": {k: round(v, 2) for k, v in total_skill_gains.items()},
        "action_log": action_log,
        "total_incidents_processed": len(incidents),
    }
