from __future__ import annotations

from dataclasses import dataclass
import os


# Logical brains. AGENT_MODEL is the actual agency/decision brain; the
# conversation model remains available for lightweight natural-language work.
MICRO_MODEL = os.getenv("ULTRON_MICRO_MODEL", "smollm2:135m-instruct-q4_0")
AGENT_MODEL = os.getenv("ULTRON_AGENT_MODEL", "qwen3:8b")
FAST_MODEL = os.getenv("ULTRON_FAST_MODEL", "qwen2.5:3b")
MID_MODEL = os.getenv("ULTRON_MID_MODEL", AGENT_MODEL)
HEAVY_MODEL = os.getenv("ULTRON_HEAVY_MODEL", "qwen3:8b")
VISION_MODEL = os.getenv("ULTRON_VISION_MODEL", "qwen2.5vl:3b")


@dataclass(frozen=True)
class Route:
    agent: str
    model: str
    max_output_tokens: int
    num_ctx: int
    history_turns: int


def route_prompt(prompt: str) -> Route:
    """Select the agency brain without hard-coded natural-language commands.

    The model itself decides whether the request is conversation, reasoning,
    clarification, or tool use. This function only chooses the capable
    orchestration brain; it does not inspect or pattern-match the user's words.
    """
    return Route("agent", AGENT_MODEL, 256, 2048, 5)
