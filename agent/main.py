from dotenv import load_dotenv
from agent.graph import build_graph
from agent.skills import discover_skills

load_dotenv()


def main():
    available = discover_skills()
    print(f"Available skills: {', '.join(available) if available else '(none)'}")
    skill_input = input("Skills to enable (comma-separated, or leave blank): ").strip()
    active_skills = [s.strip() for s in skill_input.split(",") if s.strip()] if skill_input else []

    graph = build_graph(skills=active_skills)
    config = {"configurable": {"thread_id": "1"}}

    print(f"\nLangGraph Agent ready. Skills: {active_skills or '(none)'}. Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in {"quit", "exit", "q"}:
            break

        for event in graph.stream({"messages": [("user", user_input)]}, config):
            for value in event.values():
                message = value["messages"][-1]
                if isinstance(message, tuple):
                    print(f"  {message}")
                else:
                    message.pretty_print()


if __name__ == "__main__":
    main()
