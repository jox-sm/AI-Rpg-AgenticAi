from langchain_openai import ChatOpenAI

from .tools import TOOLS


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools(TOOLS)
