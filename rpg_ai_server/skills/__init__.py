from .combat_offense import SKILLS as COMBAT_OFFENSE
from .combat_defense import SKILLS as COMBAT_DEFENSE
from .weapons import SKILLS as WEAPONS
from .magic import SKILLS as MAGIC
from .social import SKILLS as SOCIAL
from .stealth import SKILLS as STEALTH
from .crafting import SKILLS as CRAFTING
from .survival import SKILLS as SURVIVAL
from .knowledge import SKILLS as KNOWLEDGE
from .physical import SKILLS as PHYSICAL
from .strategy import SKILLS as STRATEGY

SKILL_REGISTRY: dict[str, dict] = {}
SKILL_REGISTRY.update(COMBAT_OFFENSE)
SKILL_REGISTRY.update(COMBAT_DEFENSE)
SKILL_REGISTRY.update(WEAPONS)
SKILL_REGISTRY.update(MAGIC)
SKILL_REGISTRY.update(SOCIAL)
SKILL_REGISTRY.update(STEALTH)
SKILL_REGISTRY.update(CRAFTING)
SKILL_REGISTRY.update(SURVIVAL)
SKILL_REGISTRY.update(KNOWLEDGE)
SKILL_REGISTRY.update(PHYSICAL)
SKILL_REGISTRY.update(STRATEGY)


def get_skill(name: str) -> dict | None:
    return SKILL_REGISTRY.get(name.lower())


def list_skills(category: str = "") -> list[str]:
    if category:
        return [k for k, v in SKILL_REGISTRY.items() if v.get("category") == category]
    return list(SKILL_REGISTRY.keys())


def list_categories() -> list[str]:
    cats: set[str] = set()
    for v in SKILL_REGISTRY.values():
        if "category" in v:
            cats.add(v["category"])
    return sorted(cats)
