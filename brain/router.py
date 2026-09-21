from __future__ import annotations

from dataclasses import dataclass
import os


# Logical agents share models where that is faster/cheaper on this CPU.
AGENT_MODEL = os.getenv("ULTRON_AGENT_MODEL", "qwen2.5:1.5b")
FAST_MODEL = os.getenv("ULTRON_FAST_MODEL", "qwen2.5:1.5b")
MID_MODEL = os.getenv("ULTRON_MID_MODEL", "qwen2.5:3b")
HEAVY_MODEL = os.getenv("ULTRON_HEAVY_MODEL", "qwen3:8b")


@dataclass(frozen=True)
class Route:
    agent: str
    model: str
    max_output_tokens: int
    num_ctx: int


_OPERATOR_TERMS = (
    "open ",
    "launch ",
    "start ",
    "close ",
    "quit ",
    "type ",
    "write ",
    "enter ",
    "click ",
    "press ",
    "move the mouse",
    "move mouse",
    "scroll ",
    "take a screenshot",
    "screenshot",
    "create a file",
    "make a file",
    "rename ",
    "copy ",
    "paste ",
)

_HEAVY_TERMS = (
    "build",
    "code",
    "debug",
    "refactor",
    "architect",
    "research",
    "deeply",
    "analyze",
    "analyse",
    "design a system",
    "create a project",
    "fix this project",
    "implement",
)

_MID_TERMS = (
    "explain",
    "why ",
    "how ",
    "solve ",
    "calculate",
    "math",
    "homework",
    "compare",
    "summarize",
    "teach me",
)


def route_prompt(prompt: str) -> Route:
    text = prompt.strip().casefold()

    if any(term in text for term in _OPERATOR_TERMS):
        return Route("operator", AGENT_MODEL, 80, 768)

    if len(text) > 220 or any(term in text for term in _HEAVY_TERMS):
        return Route("builder", HEAVY_MODEL, 240, 3072)

    if len(text) > 90 or any(term in text for term in _MID_TERMS):
        return Route("reasoner", MID_MODEL, 160, 1536)

    return Route("conversation", FAST_MODEL, 96, 1024)
