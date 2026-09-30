from __future__ import annotations

import os

from brain.router import AGENT_MODEL

TOOL = {
    "name": "browser_agent",
    "description": "Run a multi-step browser task with Browser Use and a local Ollama model. Use for research, navigation, forms, and browser workflows that need an agent rather than one deterministic click.",
}

def run(task: str, model: str = "") -> str:
    """Execute a natural-language browser mission with Browser Use."""
    if not task.strip():
        raise ValueError("task must not be empty")

    try:
        from browser_use import Agent, ChatOllama
    except ImportError as exc:
        raise RuntimeError(
            "Browser Use is not installed. Run "
            "scripts\\setup_ecosystem.ps1 -WithEnvironments."
        ) from exc

    selected = model.strip() or os.getenv("ULTRON_BROWSER_MODEL", AGENT_MODEL)
    llm = ChatOllama(model=selected)
    agent = Agent(task=task, llm=llm)
    history = agent.run_sync()

    if hasattr(history, "final_result"):
        result = history.final_result()
    else:
        result = history

    return str(result)
