import os
from typing import Annotated
from googleapiclient.discovery import build


def google_search(query: Annotated[str, "The search query to look up on Google"]) -> str:
    """Search Google for the given query and return top results."""
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        return "Error: GOOGLE_API_KEY or GOOGLE_CSE_ID not set in environment."

    try:
        service = build("customsearch", "v1", developerKey=api_key)
        result = service.cse().list(q=query, cx=cse_id, num=5).execute()

        items = result.get("items", [])
        if not items:
            return "No results found."

        lines = []
        for i, item in enumerate(items, 1):
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            lines.append(f"{i}. {title}\n   {link}\n   {snippet}")

        return "\n\n".join(lines)
    except Exception as e:
        return f"Error performing Google search: {e}"
