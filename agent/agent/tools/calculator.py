import math
from typing import Annotated


def calculate(expression: Annotated[str, "A mathematical expression to evaluate, e.g. '2 + 2' or 'sqrt(16)'"]) -> str:
    """Evaluate a mathematical expression."""
    allowed_names = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"Result: {result}"
    except Exception as e:
        return f"Error evaluating expression: {e}"
