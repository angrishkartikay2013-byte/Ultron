from __future__ import annotations

import re
import time
from collections import OrderedDict


class ResponseCache:
    """Tiny in-memory exact-response cache for repeated local prompts."""

    def __init__(self, max_items: int = 64, ttl_seconds: int = 1800) -> None:
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._items: OrderedDict[str, tuple[float, str]] = OrderedDict()

    @staticmethod
    def _key(prompt: str) -> str:
        return re.sub(r"\s+", " ", prompt.casefold().strip())

    def get(self, prompt: str) -> str | None:
        key = self._key(prompt)
        item = self._items.get(key)
        if item is None:
            return None

        created, value = item
        if time.monotonic() - created > self.ttl_seconds:
            self._items.pop(key, None)
            return None

        self._items.move_to_end(key)
        return value

    def put(self, prompt: str, response: str) -> None:
        if not response.strip():
            return

        key = self._key(prompt)
        self._items[key] = (time.monotonic(), response)
        self._items.move_to_end(key)

        while len(self._items) > self.max_items:
            self._items.popitem(last=False)


response_cache = ResponseCache()
