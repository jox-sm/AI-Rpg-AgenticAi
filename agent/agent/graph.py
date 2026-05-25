from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .llm import llm_with_tools
from .tools import TOOLS
from .skills import compose_instructions
from .nodes import make_agent_node


def build_graph(skills: list[str] | None = None) -> StateGraph:
    instruction = compose_instructions(skills or [])

    graph_builder = StateGraph(AgentState)

    graph_builder.add_node("agent", make_agent_node(llm_with_tools, instruction))
    graph_builder.add_node("tools", ToolNode(TOOLS))

    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges("agent", tools_condition)
    graph_builder.add_edge("tools", "agent")

    return graph_builder.compile(checkpointer=MemorySaver())
