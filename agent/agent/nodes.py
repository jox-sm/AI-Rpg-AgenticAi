from langchain_core.messages import SystemMessage

from .state import AgentState


def make_agent_node(llm_with_tools, skill_instructions: str):

    def agent_node(state: AgentState) -> dict:
        messages = list(state["messages"])
        if skill_instructions and not any(isinstance(m, SystemMessage) for m in messages):
            messages.insert(0, SystemMessage(content=skill_instructions))
        result = llm_with_tools.invoke(messages)
        return {"messages": [result]}

    return agent_node
