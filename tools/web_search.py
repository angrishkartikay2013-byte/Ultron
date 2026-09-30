from __future__ import annotations

import os
import requests

TOOL = {
    "name": "web_search",
    "description": "Search the web through SearXNG when configured. Returns grounded result titles, URLs, and snippets.",
}

def run(query: str, limit: int = 8) -> str:
    """Search a configured SearXNG JSON endpoint."""
    if not query.strip():
        raise ValueError("query must not be empty")
    endpoint = os.getenv("ULTRON_SEARXNG_URL", "").strip()
    if not endpoint:
        return (
            "No SearXNG endpoint is configured. Use the browser_agent tool for "
            "web research, or configure ULTRON_SEARXNG_URL after starting a "
            "SearXNG service."
        )

    response = requests.get(
        endpoint,
        params={"q": query, "format": "json", "language": "en"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])[: max(1, min(limit, 20))]
    if not results:
        return "No search results."

    return "\n".join(
        f"- {item.get('title', 'Untitled')}\n"
        f"  {item.get('url', '')}\n"
        f"  {item.get('content', '')[:500]}"
        for item in results
    )
