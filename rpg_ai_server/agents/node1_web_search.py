from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

import httpx
from langchain_core.tools import tool

from ..config.settings import settings
from ..schemas.state import GameState
from ..utils.logger import logger

try:
    from scrapy import Selector
except Exception:  # scrapy optional at import time, required in requirements
    Selector = None

_WS_RE = re.compile(r"\s+")

_BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def html_to_text(html: str, max_chars: int = 1500) -> str:
    """Squeeze readable text out of raw HTML. Never returns markup."""
    if not html or Selector is None:
        return ""
    try:
        sel = Selector(text=html)
    except Exception:
        return ""
    # Drop boilerplate / non-content nodes
    for bad in sel.css(
        "script, style, noscript, nav, footer, header, aside, form, iframe, "
        "button, input, select, textarea, [role='navigation'], .sidebar, .ad, .ads"
    ):
        try:
            bad.drop()
        except Exception:
            pass
    # Content-first selectors, document order preserved per selector group
    chunks: List[str] = []
    for css in (
        "title::text",
        "main h1::text, main h2::text, main h3::text, article h1::text, article h2::text, h1::text, h2::text",
        "main p::text, article p::text, .content p::text, p::text",
        "main li::text, article li::text, li::text",
    ):
        try:
            chunks.extend(t.strip() for t in sel.css(css).getall() if t and t.strip())
        except Exception:
            continue
    text = _WS_RE.sub(" ", " ".join(chunks)).strip()
    # Kill leftover boilerplate tokens from bot pages
    if len(text) < 40 and ("{" in text or "<" in text):
        return ""
    return text[:max_chars]


def _parse_ddg_results(html: str, limit: int = 3) -> List[Dict[str, str]]:
    """Parse DuckDuckGo html endpoint into [{title, snippet, url}]."""
    if not html or Selector is None:
        return []
    try:
        sel = Selector(text=html)
    except Exception:
        return []
    out: List[Dict[str, str]] = []
    for block in sel.css("div.result, div.results_links, td.result-snippet"):
        try:
            title = " ".join(t.strip() for t in block.css("a.result__a::text").getall() if t.strip())
            href = (block.css("a.result__a::attr(href)").get() or "").strip()
            snippet = " ".join(
                t.strip() for t in block.css(".result__snippet::text, .result-snippet::text").getall() if t.strip()
            )
            if not href and not title:
                continue
            # Unwrap DDG redirect //duckduckgo.com/l/?uddg=<encoded>
            if "uddg=" in href:
                try:
                    qs = parse_qs(urlparse(href).query)
                    href = unquote(qs.get("uddg", [href])[0])
                except Exception:
                    pass
            out.append({"title": title[:200], "snippet": _WS_RE.sub(" ", snippet)[:500], "url": href[:500]})
            if len(out) >= limit:
                break
        except Exception:
            continue
    return out


async def _fetch_html(url: str, timeout: float) -> str:
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": settings.models.scraper_user_agent, **_BROWSER_HEADERS},
        follow_redirects=True,
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text


async def _fetch_and_extract(url: str, timeout: float) -> str:
    """Fetch a page and return squeezed text only — never raw HTML."""
    html = await _fetch_html(url, timeout)
    return html_to_text(html)


@tool
async def scrapy_lore_search(query: str) -> str:
    """Scrape SRD-legal D&D sources for lore/rules (replaces Gemini google_search).

    Uses httpx fetch + Scrapy Selector parsing. No Google API key needed.
    Returns squeezed plain text only — never raw HTML.
    Args:
        query: 2-10 word lore query (monster/spell/rule name best)
    """
    try:
        q = (query or "").strip()[:120]
        if not q:
            return "No lore found."
        timeout = settings.models.scraper_timeout_seconds
        # Direct wiki page guess first (fast path — no www., cert rejects it),
        # then DuckDuckGo HTML fallback (parse snippets + follow top hit).
        slug = q.lower().replace(" ", "-").replace("'", "")
        parts: List[str] = []

        for url in (
            f"https://dnd5e.wikidot.com/{slug}",
            f"https://www.dndbeyond.com/monsters/{slug}",
        ):
            try:
                text = await _fetch_and_extract(url, timeout)
                if len(text) >= 80:
                    parts.append(f"[source {url}]\n{text}")
                    break
            except Exception as e:
                logger.debug(f"Scrape guess miss {url}: {e}")
                continue

        if not parts:
            ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus('dnd 5e ' + q)}"
            try:
                ddg_html = await _fetch_html(ddg_url, timeout)
                for hit in _parse_ddg_results(ddg_html):
                    line = f"{hit['title']}: {hit['snippet']}".strip(": ")
                    if line:
                        parts.append(f"[source {hit['url'] or ddg_url}]\n{line[:500]}")
                # Follow the top hit for a full squeeze (prefer wiki/srd sources)
                hits = _parse_ddg_results(ddg_html)
                for hit in hits[:2]:
                    if not hit["url"].startswith("http"):
                        continue
                    try:
                        text = await _fetch_and_extract(hit["url"], timeout)
                        if len(text) >= 80:
                            parts.append(f"[source {hit['url']}]\n{text}")
                            break
                    except Exception as e:
                        logger.warning(f"Scrape miss {hit['url']}: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Scrape miss {ddg_url}: {e}")

        text = "\n\n".join(p for p in parts if p.strip())[:1500]
        # Final guard: never leak markup upstream
        if "<" in text and ">" in text and ("<!" in text or "</" in text):
            text = html_to_text(text) or "No lore found."
        return text or "No lore found."
    except Exception as e:
        logger.error(f"Scrapy lore search failed: {e}")
        return "Search unavailable."


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
