from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MEMORY_FILE = ROOT / "memory" / "long_term.json"
MAX_ITEMS = 500


def _load() -> list[dict[str, Any]]:
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)][-MAX_ITEMS:]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return []


def _save(items: list[dict[str, Any]]) -> None:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(
        json.dumps(items[-MAX_ITEMS:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def remember(content: str, kind: str = "fact", tags: str = "") -> str:
    content = re.sub(r"\s+", " ", content.strip())
    if not content:
        raise ValueError("Memory content cannot be empty.")

    items = _load()
    now = time.time()
    item = {
        "id": uuid.uuid4().hex,
        "kind": kind.strip() or "fact",
        "content": content,
        "tags": [part.strip().lower() for part in tags.split(",") if part.strip()],
        "created_at": now,
        "updated_at": now,
    }
    items.append(item)
    _save(items)
    return f"Stored durable memory {item['id']}."


def recall(query: str, limit: int = 6) -> list[dict[str, Any]]:
    query = re.sub(r"\s+", " ", query.strip().lower())
    if not query:
        return []

    terms = {term for term in re.findall(r"[a-z0-9_]+", query) if len(term) > 1}
    scored: list[tuple[int, float, dict[str, Any]]] = []

    for item in _load():
        haystack = " ".join([
            str(item.get("content", "")).lower(),
            str(item.get("kind", "")).lower(),
            " ".join(map(str, item.get("tags", []))).lower(),
        ])
        overlap = sum(1 for term in terms if term in haystack)
        if overlap:
            scored.append((overlap, float(item.get("updated_at", 0)), item))

    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [item for _, _, item in scored[: max(1, min(int(limit), 20))]]
