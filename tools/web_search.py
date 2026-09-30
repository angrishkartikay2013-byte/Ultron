from __future__ import annotations

import os
import requests

TOOL = {
    "name": "web_search",
    "description": "Search the web through a configured SearXNG instance. Returns grounded result titles, URLs, and snippets.",
}

def run(query: str, limit: int = 8) -> str:
    """Search SearXNG JSON API without requiring a cloud search API key."""
    endpoint = os.getenv("ULTRON_SEARXNG_URL", "http://127.0.0.1:8080/search")
    response = requests.get(
        endpoint,
        params={"q": query, "format": "json", "language": "en"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])[:max(1, min(limit, 20))]
    if not results:
        return "No search results."
    lines = []
    for item in results:
        lines.append(
            f"- {item.get('title','Untitled')}\n"
            f"  {item.get('url','')}\n"
            f"  {item.get('content','')[:500]}"
        )
    return "\n".join(lines)
