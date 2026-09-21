from __future__ import annotations

import json
from pathlib import Path

from .llm import chat

MEMORY_FILE = Path("memory") / "conversation.json"
MAX_MESSAGES = 40

history: list[dict[str, str]] = []


def _load() -> None:
    global history
    try:
        raw = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            history = [
                item
                for item in raw[-MAX_MESSAGES:]
                if isinstance(item, dict)
                and item.get("role") in {"user", "assistant"}
                and isinstance(item.get("content"), str)
            ]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        history = []


def _save() -> None:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(
        json.dumps(history[-MAX_MESSAGES:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def reset_memory() -> None:
    history.clear()
    _save()


def ask(prompt: str) -> str:
    prompt = prompt.strip()
    if not prompt:
        return ""

    quick = QUICK_REPLIES.get(prompt.casefold())
    if quick:
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": quick})
        del history[:-MAX_MESSAGES]
        _save()
        return quick

    history.append({"role": "user", "content": prompt})
    del history[:-MAX_MESSAGES]
    reply = chat(history).strip()

    history.append({"role": "assistant", "content": reply})
    del history[:-MAX_MESSAGES]
    _save()

    return reply


_load()
