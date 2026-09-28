from __future__ import annotations

import json

from memory.store import recall as search_memory
from memory.store import remember as save_memory


TOOL = {
    "name": "memory",
    "description": (
        "Store or recall durable ULTRON memory. Use action='remember' for stable "
        "facts, preferences, project decisions, names, or long-lived plans. "
        "Use action='recall' to search previously stored memory."
    ),
}


def run(
    action: str,
    query: str = "",
    content: str = "",
    kind: str = "fact",
    tags: str = "",
    limit: int = 6,
) -> str:
    action = action.strip().lower()

    if action == "remember":
        return save_memory(content, kind=kind, tags=tags)

    if action == "recall":
        return json.dumps(search_memory(query, limit=limit), ensure_ascii=False)

    raise ValueError("action must be 'remember' or 'recall'.")
