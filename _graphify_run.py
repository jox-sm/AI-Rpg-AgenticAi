"""Patch graphify to use OpenRouter, then run extraction."""
import os, sys
from pathlib import Path

def main():
    # Source .env file
    env_path = Path("D:/AI agent/rpg_ai_server/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

    # Patch graphify backends to use OpenRouter
    import graphify.llm as llm
    llm.BACKENDS["openai"]["base_url"] = "https://openrouter.ai/api/v1"
    llm.BACKENDS["openai"]["default_model"] = "cohere/north-mini-code:free"
    os.environ["GRAPHIFY_OPENAI_MODEL"] = "cohere/north-mini-code:free"
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "")

    print(f"Backend: openai -> {llm.BACKENDS['openai']['base_url']}")
    print(f"Model: {llm.BACKENDS['openai']['default_model']}")
    print(f"API Key set: {bool(os.environ.get('OPENAI_API_KEY'))}")

    # Run extraction
    target = sys.argv[1] if len(sys.argv) > 1 else "D:/AI agent"
    from graphify.__main__ import main as graphify_main
    sys.argv = ["graphify", "extract", str(target), "--backend", "openai", "--no-cluster", "--max-concurrency", "2"]
    graphify_main()

if __name__ == "__main__":
    main()
