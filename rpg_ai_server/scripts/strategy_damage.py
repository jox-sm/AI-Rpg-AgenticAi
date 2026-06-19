from __future__ import annotations

import math
import random
from typing import Optional

from .combat_system import DAMAGE_TYPE_EFFECTIVENESS, resistance_modifier, STATUS_EFFECTS
from .dice_engine import roll_total, Dice

ENVIRONMENTAL_HAZARDS: dict[str, dict] = {
    "fire": {
        "base_damage": 25,
        "damage_type": "fire",
        "aoe": True,
        "status": "burn",
        "status_chance": 1.0,
        "description": "Engulfed in flames",
        "lethality": "lethal",
        "breath_hazard": True,
    },
    "explosion": {
        "base_damage": 60,
        "damage_type": "fire",
        "aoe": True,
        "status": "burn",
        "status_chance": 1.0,
        "description": "Shockwave and shrapnel",
        "lethality": "certain_death",
        "breath_hazard": False,
    },
    "smoke": {
        "base_damage": 15,
        "damage_type": "poison",
        "aoe": True,
        "status": "poison",
        "status_chance": 1.0,
        "description": "Smoke fills the lungs",
        "lethality": "lethal",
        "breath_hazard": True,
    },
    "gas": {
        "base_damage": 20,
        "damage_type": "poison",
        "aoe": True,
        "status": "poison",
        "status_chance": 1.0,
        "description": "Toxic fumes",
        "lethality": "lethal",
        "breath_hazard": True,
    },
    "crushing": {
        "base_damage": 50,
        "damage_type": "bludgeoning",
        "aoe": True,
        "status": "stun",
        "status_chance": 0.5,
        "description": "Collapsing debris",
        "lethality": "lethal",
        "breath_hazard": False,
    },
    "drowning": {
        "base_damage": 20,
        "damage_type": "force",
        "aoe": True,
        "status": "slow",
        "status_chance": 1.0,
        "description": "Flooding water filling the space",
        "lethality": "certain_death",
        "breath_hazard": True,
    },
    "cold": {
        "base_damage": 15,
        "damage_type": "cold",
        "aoe": True,
        "status": "freeze",
        "status_chance": 0.7,
        "description": "Freezing blast",
        "lethality": "dangerous",
        "breath_hazard": False,
    },
    "lightning": {
        "base_damage": 35,
        "damage_type": "lightning",
        "aoe": True,
        "status": "stun",
        "status_chance": 0.9,
        "description": "Electrical discharge",
        "lethality": "lethal",
        "breath_hazard": False,
    },
    "acid": {
        "base_damage": 30,
        "damage_type": "acid",
        "aoe": True,
        "status": "poison",
        "status_chance": 0.6,
        "description": "Corrosive spray",
        "lethality": "lethal",
        "breath_hazard": True,
    },
    "radiant": {
        "base_damage": 40,
        "damage_type": "radiant",
        "aoe": True,
        "status": "blind",
        "status_chance": 0.6,
        "description": "Holy radiance",
        "lethality": "dangerous",
        "breath_hazard": False,
    },
    "impact": {
        "base_damage": 30,
        "damage_type": "bludgeoning",
        "aoe": False,
        "status": "stun",
        "status_chance": 0.4,
        "description": "Heavy impact",
        "lethality": "dangerous",
        "breath_hazard": False,
    },
}

AMPLIFIER_MAP: dict[str, dict] = {
    "confined_space": {
        "multiplier": 2.0,
        "enclosure_tier": "confined",
        "description": "Tight space — hazard concentrates",
    },
    "sealed": {
        "multiplier": 3.0,
        "enclosure_tier": "sealed",
        "description": "Completely sealed — no escape, no ventilation",
    },
    "flammable_material": {
        "multiplier": 2.5,
        "description": "Coal, oil, dry wood, gas — adds fuel to the fire",
        "triggers": ["fire", "explosion"],
    },
    "explosive_material": {
        "multiplier": 3.5,
        "description": "Black powder, alchemist fire — chain detonation",
        "triggers": ["fire", "explosion", "lightning"],
    },
    "conductive": {
        "multiplier": 2.0,
        "description": "Water or metal — spreads lightning to all targets",
        "triggers": ["lightning"],
    },
    "height_advantage": {
        "multiplier": 1.5,
        "description": "Dropping from above adds momentum",
    },
    "structural_weakness": {
        "multiplier": 2.0,
        "description": "Rotting beams, cracked ceiling — collapse imminent",
    },
    "chain_reaction": {
        "multiplier": 4.0,
        "description": "Multiple elements cascade into catastrophe",
    },
    "no_ventilation": {
        "multiplier": 2.5,
        "description": "Smoke and heat have nowhere to go",
        "triggers": ["fire", "smoke", "gas", "poison"],
    },
    "fuel_soaked": {
        "multiplier": 3.0,
        "description": "Targets are drenched in oil, alcohol, or accelerant",
        "triggers": ["fire", "explosion"],
    },
}

PLAN_QUALITY_HAZARD_BONUS: dict[str, float] = {
    "none": 0.4,
    "reckless": 0.3,
    "poor": 0.6,
    "average": 1.0,
    "good": 1.5,
    "excellent": 2.5,
    "genius": 4.0,
}

WALL_MATERIALS: dict[str, dict] = {
    "paper": {"min_strength": 1, "min_level": 1, "description": "Thin paper or cloth"},
    "wood": {"min_strength": 5, "min_level": 3, "description": "Wooden planks or door"},
    "stone": {"min_strength": 15, "min_level": 8, "description": "Solid stone masonry"},
    "reinforced_stone": {"min_strength": 25, "min_level": 12, "description": "Stone reinforced with metal beams"},
    "metal": {"min_strength": 35, "min_level": 16, "description": "Solid iron or steel"},
    "magical": {"min_strength": 50, "min_level": 20, "description": "Magically reinforced barrier"},
}

ENCLOSURE_TIERS = ["open", "confined", "sealed"]

DEFAULT_MATERIAL_BY_ENCLOSURE = {
    "open": "paper",
    "confined": "wood",
    "sealed": "stone",
}


def _get_escape_dc(
    enclosure: str,
    wall_material: str = "",
    ventilation: bool = False,
) -> dict:
    wall = WALL_MATERIALS.get(wall_material, WALL_MATERIALS["stone"])

    if enclosure == "open":
        return {
            "can_escape": True,
            "escape_dc": 0,
            "escape_time": "instant",
            "reason": "Area is open — no barrier to escape",
        }

    if enclosure == "confined":
        return {
            "can_escape": True,
            "escape_dc": max(5, wall["min_level"]),
            "escape_time": "1 action",
            "reason": f"Must break through {wall['description']} (DC {max(5, wall['min_level'])})",
        }

    if enclosure == "sealed" and ventilation:
        return {
            "can_escape": True,
            "escape_dc": wall["min_level"],
            "escape_time": "1-2 actions",
            "reason": f"Small ventilation — can escape but must break {wall['description']} (DC {wall['min_level']})",
        }

    return {
        "can_escape": False,
        "escape_dc": wall["min_level"],
        "escape_time": "multiple actions",
        "reason": f"Sealed behind {wall['description']} (DC {wall['min_level']}) — no quick escape",
    }


def evaluate_strategy(
    player_level: int = 1,
    plan_quality: str = "average",
    hazard_type: str = "fire",
    amplifiers: Optional[list[str]] = None,
    enclosure: str = "open",
    wall_material: str = "",
    ventilation: bool = False,
    target_count: int = 1,
    target_types: Optional[list[str]] = None,
    target_levels: Optional[list[int]] = None,
    target_hp: Optional[list[int]] = None,
    target_resistances: Optional[list[dict[str, float]]] = None,
) -> dict:
    amps = amplifiers or []
    ttypes = target_types or ["flesh"] * target_count
    tlevels = target_levels or [max(1, player_level)] * target_count
    thp = target_hp or [lvl * 15 + 20 for lvl in tlevels]
    tres = target_resistances or [{}] * target_count

    while len(ttypes) < target_count:
        ttypes.append("flesh")
    while len(tlevels) < target_count:
        tlevels.append(max(1, player_level))
    while len(thp) < target_count:
        thp.append(tlevels[-1] * 15 + 20)
    while len(tres) < target_count:
        tres.append({})

    hazard = ENVIRONMENTAL_HAZARDS.get(hazard_type)
    if not hazard:
        return {"error": f"Unknown hazard type: {hazard_type}"}

    if not wall_material:
        wall_material = DEFAULT_MATERIAL_BY_ENCLOSURE.get(enclosure, "stone")

    plan_mult = PLAN_QUALITY_HAZARD_BONUS.get(plan_quality, 1.0)
    base_damage = hazard["base_damage"]
    dmg_type = hazard["damage_type"]
    lethality = hazard["lethality"]
    breath_hazard = hazard["breath_hazard"]

    total_amp_mult = 1.0
    enclosure_tier = enclosure
    applied_amps: list[str] = []

    for amp_name in amps:
        amp = AMPLIFIER_MAP.get(amp_name)
        if not amp:
            continue
        triggers = amp.get("triggers")
        if triggers and hazard_type not in triggers:
            continue

        new_tier = amp.get("enclosure_tier")
        if new_tier:
            current_idx = ENCLOSURE_TIERS.index(enclosure_tier) if enclosure_tier in ENCLOSURE_TIERS else 0
            new_idx = ENCLOSURE_TIERS.index(new_tier)
            if new_idx > current_idx:
                enclosure_tier = new_tier
                if new_tier == "sealed":
                    ventilation = False

        total_amp_mult *= amp.get("multiplier", 1.0)
        applied_amps.append(amp_name)

    if "chain_reaction" in applied_amps and len(applied_amps) >= 2:
        total_amp_mult *= 5.0

    escape_info = _get_escape_dc(enclosure_tier, wall_material, ventilation)
    can_escape = escape_info["can_escape"]
    escape_dc = escape_info["escape_dc"]

    scene_info_parts = [
        f"Hazard: {hazard['description']}",
        f"Enclosure: {enclosure_tier}, walls: {wall_material}",
        f"Ventilation: {'yes' if ventilation else 'no'}, breath hazard: {'yes' if breath_hazard else 'no'}",
        f"Escape: {escape_info['reason']}",
    ]

    targets: list[dict] = []
    total_damage_dealt = 0
    kills = 0

    for i in range(target_count):
        tt = ttypes[i] if i < len(ttypes) else "flesh"
        lvl = tlevels[i] if i < len(tlevels) else max(1, player_level)
        hp = thp[i] if i < len(thp) else 50
        res = tres[i] if i < len(tres) else {}

        element_mult = resistance_modifier(dmg_type, tt, res)

        if element_mult == 0.0:
            targets.append(_make_target_result(i, tt, lvl, hp, 0, False, immune=True, element_mult=0.0))
            continue

        if lvl >= 20:
            element_mult = min(element_mult, 0.5)

        if tt.lower() in ("construct", "undead", "elemental", "golem") and breath_hazard:
            targets.append(_make_target_result(i, tt, lvl, hp, 0, False, immune=True, reason="Does not breathe", element_mult=element_mult))
            continue

        can_break_wall = lvl >= escape_dc and lvl > 0
        wall_break_time = max(1, escape_dc - lvl + 1) if not can_break_wall else 0

        trapped = not can_break_wall and enclosure_tier != "open"

        damage_taken = 0
        dead = False
        outcome = ""
        status_applied = False

        if trapped:
            if breath_hazard and enclosure_tier == "sealed":
                lethal_bonus = 2.0 if not ventilation else 1.5
                scene_mult = plan_mult * total_amp_mult * element_mult * lethal_bonus
                raw = base_damage * scene_mult
                raw += hp * 0.5
                damage_taken = max(1, int(raw * (roll_total(Dice.D6) / 3.5)))
                damage_taken = min(damage_taken, hp)
                dead = True
                outcome = "instant_death_trapped"
            elif lethality in ("certain_death", "lethal"):
                scene_mult = plan_mult * total_amp_mult * element_mult
                raw = base_damage * scene_mult
                damage_taken = max(1, int(raw * (roll_total(Dice.D6) / 3.5)))
                if damage_taken >= hp * 0.8:
                    damage_taken = hp
                    dead = True
                    outcome = "killed_by_hazard"
                else:
                    damage_taken = min(damage_taken, hp)
                    outcome = "survived_hazard"
            else:
                scene_mult = plan_mult * total_amp_mult * element_mult
                raw = base_damage * scene_mult
                damage_taken = max(1, int(raw * (roll_total(Dice.D6) / 3.5)))
                damage_taken = min(damage_taken, hp)
                outcome = "damaged_trapped"

            if random.random() < 0.3:
                status_applied = True

        elif can_break_wall:
            escape_delay = max(1, escape_dc - lvl) if escape_dc > lvl else 0
            exposure_mult = 0.3 + (escape_delay * 0.2)
            scene_mult = plan_mult * total_amp_mult * element_mult * exposure_mult
            raw = base_damage * scene_mult / 2
            damage_taken = max(1, int(raw * (roll_total(Dice.D6) / 3.5)))
            damage_taken = min(damage_taken, int(hp * 0.4))
            outcome = "escaped_with_damage"

            if random.random() < 0.2:
                status_applied = True
        else:
            scene_mult = plan_mult * total_amp_mult * element_mult
            raw = base_damage * scene_mult * 0.3
            damage_taken = max(1, int(raw * (roll_total(Dice.D6) / 3.5)))
            damage_taken = min(damage_taken, int(hp * 0.15))
            outcome = "open_area_damage"

        hp_after = max(0, hp - damage_taken)
        dead = dead or hp_after <= 0
        if dead:
            kills += 1

        targets.append(_make_target_result(
            i, tt, lvl, hp, damage_taken, dead,
            hp_after=hp_after, outcome=outcome, immune=False,
            can_break_wall=can_break_wall, escape_dc=escape_dc,
            trapped=trapped, element_mult=element_mult,
            status_applied=status_applied,
            status_name=hazard.get("status", "") if status_applied else None,
        ))
        total_damage_dealt += damage_taken

    all_dead = all(t.get("dead", False) for t in targets if not t.get("immune"))

    return {
        "strategy_summary": _build_v2_summary(hazard, dmg_type, enclosure_tier, wall_material, ventilation, total_damage_dealt, kills, target_count, all_dead, applied_amps, plan_mult, total_amp_mult, targets, escape_info, plan_quality),
        "player_level": player_level,
        "plan_quality": plan_quality,
        "plan_multiplier": plan_mult,
        "hazard_type": hazard_type,
        "hazard_description": hazard["description"],
        "damage_type": dmg_type,
        "lethality": lethality,
        "breath_hazard": breath_hazard,
        "enclosure": enclosure_tier,
        "wall_material": wall_material,
        "ventilation": ventilation,
        "escape_info": escape_info,
        "amplifiers": applied_amps,
        "total_amplifier_multiplier": round(total_amp_mult, 2),
        "scene_multiplier": round(plan_mult * total_amp_mult, 2),
        "total_damage_dealt": total_damage_dealt,
        "kills": kills,
        "total_targets": target_count,
        "all_dead": all_dead,
        "targets": targets,
    }


def _make_target_result(
    index: int, tt: str, lvl: int, hp_before: int, dmg: int, dead: bool,
    hp_after: int = 0, outcome: str = "", immune: bool = False,
    can_break_wall: bool = False, escape_dc: int = 0, trapped: bool = False,
    element_mult: float = 1.0, status_applied: bool = False,
    status_name: Optional[str] = None, reason: str = "",
) -> dict:
    return {
        "index": index,
        "type": tt,
        "level": lvl,
        "hp_before": hp_before,
        "hp_after": hp_after or max(0, hp_before - dmg),
        "damage_taken": dmg,
        "dead": dead,
        "immune": immune,
        "immune_reason": reason if immune else "",
        "outcome": outcome,
        "can_break_wall": can_break_wall,
        "escape_dc": escape_dc,
        "trapped": trapped,
        "element_multiplier": round(element_mult, 2),
        "status_applied": status_applied,
        "status": status_name if status_applied else None,
    }


def _build_v2_summary(hazard, dmg_type, enclosure, wall, ventilation, total_damage, kills, total_targets, all_dead, amps, plan_mult, amp_mult, targets, escape_info, plan_quality) -> str:
    parts = []

    scene = f"{enclosure} {wall} chamber" + (" (ventilated)" if ventilation else "")
    if all_dead:
        parts.append(f"The {hazard['description'].lower()} in the {scene} kills all {total_targets} targets!")
    elif kills > 0:
        parts.append(f"The {hazard['description'].lower()} in the {scene} kills {kills}/{total_targets} and deals {total_damage} total {dmg_type} damage")
    else:
        parts.append(f"The {hazard['description'].lower()} in the {scene} deals {total_damage} {dmg_type} damage across {total_targets} targets")

    if amps:
        parts.append(f"Amplified by: {', '.join(amps)} ({round(amp_mult, 1)}x)")
    if plan_mult != 1.0:
        parts.append(f"Plan quality ({plan_quality}): {plan_mult}x")
    parts.append(f"Escape: {escape_info['reason']}")

    lines = [f"Target {t['index']+1} (lvl {t['level']} {t['type']}): {t['outcome'].replace('_', ' ')} — {t['damage_taken']} dmg" + (" DEAD" if t['dead'] else "") + (" IMMUNE" if t['immune'] else "") for t in targets]
    parts.append(" | ".join(lines))

    return ". ".join(parts)


def chain_reaction_damage(
    player_level: int = 1,
    primary_hazard: str = "fire",
    secondary_hazard: str = "explosion",
    amplifiers: Optional[list[str]] = None,
    enclosure: str = "open",
    wall_material: str = "",
    ventilation: bool = False,
    target_count: int = 1,
    target_types: Optional[list[str]] = None,
    target_levels: Optional[list[int]] = None,
    target_hp: Optional[list[int]] = None,
    target_resistances: Optional[list[dict[str, float]]] = None,
) -> dict:
    amps = list(amplifiers or [])
    if "chain_reaction" not in amps:
        amps.append("chain_reaction")

    primary = evaluate_strategy(
        player_level=player_level,
        plan_quality="excellent",
        hazard_type=primary_hazard,
        amplifiers=amps,
        enclosure=enclosure,
        wall_material=wall_material,
        ventilation=ventilation,
        target_count=target_count,
        target_types=target_types,
        target_levels=target_levels,
        target_hp=target_hp,
        target_resistances=target_resistances,
    )

    if primary.get("all_dead"):
        return primary

    survivors = [t for t in primary.get("targets", []) if not t.get("dead") and not t.get("immune")]
    if not survivors:
        return primary

    secondary = evaluate_strategy(
        player_level=player_level,
        plan_quality="excellent",
        hazard_type=secondary_hazard,
        amplifiers=amps,
        enclosure=enclosure,
        wall_material=wall_material,
        ventilation=ventilation,
        target_count=len(survivors),
        target_types=[s["type"] for s in survivors],
        target_levels=[s["level"] for s in survivors],
        target_hp=[s["hp_after"] for s in survivors],
    )

    return _merge_chain(primary, secondary, target_count)


def _merge_chain(primary: dict, secondary: dict, target_count: int) -> dict:
    all_dead = primary.get("all_dead", False) or secondary.get("all_dead", False)
    total_damage = primary.get("total_damage_dealt", 0) + secondary.get("total_damage_dealt", 0)
    kills = primary.get("kills", 0) + secondary.get("kills", 0)

    return {
        "strategy_summary": f"{primary['strategy_summary']}. Then {secondary['strategy_summary']}. Chain reaction kills {kills}/{target_count}!",
        "chain_reaction": True,
        "primary": primary,
        "secondary": secondary,
        "total_damage_dealt": total_damage,
        "kills": kills,
        "total_targets": target_count,
        "all_dead": all_dead,
    }
