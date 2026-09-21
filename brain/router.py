from __future__ import annotations

from dataclasses import dataclass
import os


# Agents are logical roles. The tiny reflex model is optional; if it is not
# installed, the runtime falls back to the existing 1.5B model.
AGENT_MODEL = os.getenv("ULTRON_AGENT_MODEL", "qwen2.5:0.5b-instruct")
FAST_MODEL = os.getenv("ULTRON_FAST_MODEL", "qwen2.5:1.5b")
MID_MODEL = os.getenv("ULTRON_MID_MODEL", "qwen2.5:3b")
HEAVY_MODEL = os.getenv("ULTRON_HEAVY_MODEL", "qwen3:8b")
VISION_MODEL = os.getenv("ULTRON_VISION_MODEL", "qwen2.5vl:3b")


@dataclass(frozen=True)
class Route:
    agent: str
    model: str
    max_output_tokens: int
    num_ctx: int
    history_turns: int


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
    length = len(text)

    if any(term in text for term in _OPERATOR_TERMS):
        return Route("operator", AGENT_MODEL, 64, 640, 1)

    if length > 220 or any(term in text for term in _HEAVY_TERMS):
        return Route("builder", HEAVY_MODEL, 192, 2048, 4)

    if length > 90 or any(term in text for term in _MID_TERMS):
        return Route("reasoner", MID_MODEL, 128, 1024, 3)

    # Normal conversation is intentionally tiny: short context + short output.
    return Route("conversation", AGENT_MODEL, 64, 512, 1)
