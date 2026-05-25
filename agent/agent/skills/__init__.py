import importlib
import pkgutil


def discover_skills() -> list[str]:
    return [name for _, name, _ in pkgutil.iter_modules(__path__)]


def load_instruction(skill_name: str) -> str:
    module = importlib.import_module(f".{skill_name}", __package__)
    return module.get_instruction()


def compose_instructions(skill_names: list[str]) -> str:
    parts = []
    for name in skill_names:
        try:
            parts.append(load_instruction(name))
        except (ImportError, AttributeError):
            pass
    return "\n\n".join(parts)
