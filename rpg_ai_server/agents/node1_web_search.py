from __future__ import annotations

from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain.agents import create_agent

from ..config.settings import settings
from ..config.models import create_gemini_model
from ..schemas.state import GameState
from ..utils.logger import logger


@tool
async def google_web_search(query: str) -> str:
    """Search the web for real-time information.
    Use this tool when the game requires current facts, lore verification,
    or real-world information that the model cannot know internally.

    Args:
        query: The search query string (2-10 words for best results)
    """
    try:
        search_model = ChatGoogleGenerativeAI(
            model=settings.models.gemini_model,
            temperature=0.0,
            google_api_key=settings.app.google_api_key,
        )
        search_model_with_search = search_model.bind_tools(
            [{"google_search": {}}],
            tool_choice="google_search",
        )
        result = await search_model_with_search.ainvoke(query)
        return str(result.content)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Search unavailable: {e}"


async def node1_web_search(state: GameState) -> Dict[str, Any]:
    logger.info(f"[Node 1] Web search triggered for UUID {state['uuid']}")
    search_query = state.get("decision", None)
    query = state["prompt"]
    if search_query and hasattr(search_query, "search_query") and search_query.search_query:
        query = search_query.search_query

    try:
        agent = create_agent(
            model=create_gemini_model(temperature=0.3),
            tools=[google_web_search],
            system_prompt=(
                "You are a D&D lore researcher. Search the web for accurate information "
                "about monsters, items, spells, locations, and rules when the game requires it. "
                "Return factual data that the game master can use."
            ),
        )
        result = await agent.ainvoke({
            "messages": [
                {"role": "system", "content": f"Research needed for game UUID: {state['uuid']}"},
                {"role": "user", "content": query},
            ]
        })
        search_results = result["messages"][-1].content
    except Exception as e:
        logger.error(f"Node 1 web search agent failed: {e}")
        search_results = f"Search error: {e}"

    return {
        "search_results": search_results,
        "needs_search": False,
    }
