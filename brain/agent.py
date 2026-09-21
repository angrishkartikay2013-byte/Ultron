from __future__ import annotations

import json
from typing import Any

from brain import history, _save
from brain.llm import chat
from tools.executor import execute
from tools.registry import prompt_catalog

AGENT_INSTRUCTIONS = (
    "You are ULTRON's action router. Return exactly one JSON object and no markdown. "
    "For ordinary conversation use mode=reply with response and empty mission. "
    "For desktop actions use mode=mission with a concise response and a mission list. "
    "Only use tools from the catalog. Never invent tools. Keep missions minimal. "
    "Use wait when needed between desktop steps. Do not output commentary outside JSON."
)

def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("ULTRON returned no JSON object.")
    value = json.loads(text[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("ULTRON returned an invalid JSON root.")
    return value

def handle_prompt(prompt: str) -> str:
    prompt = prompt.strip()
    if not prompt:
        return ""

    catalog = prompt_catalog()
    context = list(history[-20:]) + [{"role": "user", "content": prompt}]
    routed = chat(
        context,
        system_extra=AGENT_INSTRUCTIONS + "\n\nAVAILABLE TOOLS:\n" + catalog,
    )

    data = _extract_json(routed)
    mode = data.get("mode")
    response = str(data.get("response", "")).strip()
    mission = data.get("mission", [])

    if mode == "mission":
        if not isinstance(mission, list) or not mission:
            raise ValueError("ULTRON selected mission mode without a mission.")
        results = execute(mission)
        failed = next((item for item in results if not item.get("ok")), None)
        if failed:
            response = response or f"Mission stopped at step {failed.get('step')}."
            response += f" Error: {failed.get('error', 'unknown error')}."
        else:
            response = response or "Mission complete."
    elif mode != "reply":
        raise ValueError(f"Unknown ULTRON mode: {mode!r}")

    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    del history[:-40]
    _save()
    return response
