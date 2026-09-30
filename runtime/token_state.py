from __future__ import annotations

from dataclasses import dataclass
import threading


@dataclass(frozen=True)
class TokenSnapshot:
    model: str = ""
    context_limit: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    remaining_tokens: int = 0


_lock = threading.Lock()
_snapshot = TokenSnapshot()


def update(
    *,
    model: str,
    context_limit: int,
    prompt_tokens: int,
    output_tokens: int,
) -> None:
    remaining = max(0, int(context_limit) - int(prompt_tokens) - int(output_tokens))
    snapshot = TokenSnapshot(
        model=str(model),
        context_limit=max(0, int(context_limit)),
        prompt_tokens=max(0, int(prompt_tokens)),
        output_tokens=max(0, int(output_tokens)),
        remaining_tokens=remaining,
    )
    with _lock:
        global _snapshot
        _snapshot = snapshot


def reset(*, model: str = "", context_limit: int = 0) -> None:
    update(
        model=model,
        context_limit=context_limit,
        prompt_tokens=0,
        output_tokens=0,
    )


def get() -> TokenSnapshot:
    with _lock:
        return _snapshot
