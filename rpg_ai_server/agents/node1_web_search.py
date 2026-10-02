from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import quote_plus

import httpx
from langchain_core.tools import tool

from ..config.settings import settings
from ..schemas.state import GameState
from ..utils.logger import logger

try:
    from scrapy import Selector
except Exception:  # scrapy optional at import time, required in requirements
    Selector = None


async def _fetch_and_extract(url: str, timeout: float) -> str:
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": settings.models.scraper_user_agent},
        follow_redirects=True,
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        html = r.text
    if Selector is None:
        return html[:1500]
    sel = Selector(text=html)
    # Strip scripts/styles, keep readable text
    for bad in sel.css("script, style, nav, footer, header"):
        bad.drop()
    text = " ".join(t.strip() for t in sel.css("main p::text, article p::text, p::text").getall() if t.strip())
    return text[:1500] if text else html[:1500]


@tool
async def scrapy_lore_search(query: str) -> str:
    """Scrape SRD-legal D&D sources for lore/rules (replaces Gemini google_search).

    Uses httpx fetch + Scrapy Selector parsing. No Google API key needed.
    Args:
        query: 2-10 word lore query (monster/spell/rule name best)
    """
    try:
        q = (query or "")[:120]
        # Direct wiki page guess first (fast path), then DuckDuckGo HTML fallback
        slug = q.lower().replace(" ", "-").replace("'", "")
        candidates = [
            f"https://www.dnd5e.wikidot.com/{slug}",
            f"https://html.duckduckgo.com/html/?q={quote_plus('dnd 5e ' + q)}",
        ]
        parts: List[str] = []
        for url in candidates:
            try:
                parts.append(f"[source {url}]\n" + await _fetch_and_extract(url, settings.models.scraper_timeout_seconds))
                if parts[-1].strip():
                    break
            except Exception as e:
                logger.warning(f"Scrape miss {url}: {e}")
                continue
        text = "\n\n".join(p for p in parts if p.strip())[:1500]
        return text or "No lore found."
    except Exception as e:
        logger.error(f"Scrapy lore search failed: {e}")
        return f"Search unavailable: {e}"


# Legacy alias (was Gemini google_search tool; kept so old imports don't break)
async def google_web_search(query: str) -> str:
    return await scrapy_lore_search.ainvoke({"query": query})


async def node1_web_search(state: GameState) -> Dict[str, Any]:
    logger.info(f"[Node 1] Scrapy lore search for UUID {state.get('uuid')}")
    decision = state.get("decision_report") or {}
    query = state.get("prompt", "")
    if isinstance(decision, dict) and decision.get("search_query"):
        query = decision["search_query"]
    elif state.get("decision") and hasattr(state["decision"], "search_query"):
        try:
            if state["decision"].search_query:
                query = state["decision"].search_query
        except Exception:
            pass
    try:
        search_results = await scrapy_lore_search.ainvoke({"query": query})
        if not isinstance(search_results, str):
            search_results = str(search_results)
    except Exception as e:
        logger.error(f"Node 1 scrapy search failed: {e}")
        search_results = f"Search error: {e}"
    return {
        "search_results": search_results[:2000],
        "needs_search": False,
    }
