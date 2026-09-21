from __future__ import annotations

import json
import re
from typing import Any

from .core import history, _save
from .llm import FAST_MODEL, HEAVY_MODEL, chat
from tools.executor import execute
from tools.registry import prompt_catalog

QUICK_REPLIES = {
    "hi": "Hello, Founder. I am online.",
    "hello": "Hello, Founder. I am online.",
    "hey": "Hey, Founder. ULTRON is online.",
    "good morning": "Good morning, Founder.",
    "good night": "Good night, Founder.",
    "thanks": "Always, Founder.",
    "thank you": "Always, Founder.",
}

ROUTER_PROMPT = """You are ULTRON's action router.
Return exactly one JSON object and no markdown.

Conversation:
{"mode":"reply","response":"...","mission":[]}

Desktop action:
{"mode":"mission","response":"...","mission":[
  {"tool":"open_app","arguments":{"app":"notepad"}},
  {"tool":"wait","arguments":{"seconds":1}},
  {"tool":"type_text","arguments":{"text":"I was here"}}
]}

Rules:
- Only use listed tools.
- Use the exact argument names shown in each tool signature.
- Never omit required information.
- Use multiple steps when needed.
- Keep responses short.
"""


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


def _direct_mission(prompt: str) -> list[dict[str, Any]] | None:
    text = prompt.strip()

    match = re.match(
        r"^(?:open|launch|start)\s+(.+?)\s+(?:and|then)\s+(?:type|write|enter)\s+(.+)$",
        text,
        flags=re.I,
    )
    if match:
        app = match.group(1).strip(" .")
        value = match.group(2).strip()

        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            value = value[1:-1]

        return [
            {"tool": "open_app", "arguments": {"app": app}},
            {"tool": "wait", "arguments": {"seconds": 0.8}},
            {"tool": "type_text", "arguments": {"text": value}},
        ]

    match = re.match(r"^(?:open|launch|start)\s+(.+)$", text, flags=re.I)
    if match and len(text.split()) <= 8:
        return [
            {"tool": "open_app", "arguments": {"app": match.group(1).strip(" .")}}
        ]

    match = re.match(
        r"^(?:move|put)\s+(?:the\s+)?mouse\s+(?:to|at)\s+(.+)$",
        text,
        flags=re.I,
    )
    if match:
        position = match.group(1).strip(" .")
        coordinate = re.match(
            r"^\(?\s*(\d+)\s*[, ]\s*(\d+)\s*\)?$",
            position,
        )
        if coordinate:
            return [{
                "tool": "mouse_move",
                "arguments": {
                    "x": int(coordinate.group(1)),
                    "y": int(coordinate.group(2)),
                },
            }]
        return [{"tool": "mouse_move", "arguments": {"position": position}}]

    return None


def _is_heavy_task(prompt: str) -> bool:
    keywords = (
        "write code",
        "build",
        "debug",
        "research",
        "analyze",
        "analyse",
        "plan",
        "design",
        "create a project",
        "fix this",
        "explain deeply",
        "step by step",
    )
    lowered = prompt.casefold()
    return len(prompt) > 180 or any(keyword in lowered for keyword in keywords)


def _run_model_router(
    prompt: str,
    forced_model: str | None = None,
) -> tuple[dict[str, Any], str]:
    catalog = prompt_catalog()
    context = list(history[-12:]) + [{"role": "user", "content": prompt}]
    model = forced_model or (HEAVY_MODEL if _is_heavy_task(prompt) else FAST_MODEL)
    extra = ROUTER_PROMPT + "\n\nAVAILABLE TOOLS:\n" + catalog

    try:
        routed = chat(
            context,
            system_extra=extra,
            model=model,
            max_output_tokens=220 if model == FAST_MODEL else 420,
        )
        return _extract_json(routed), model
    except Exception:
        if model == HEAVY_MODEL:
            raise

        routed = chat(
            context,
            system_extra=extra
            + "\n\nFast router failed. Be strict about JSON and tool arguments.",
            model=HEAVY_MODEL,
            max_output_tokens=420,
        )
        return _extract_json(routed), HEAVY_MODEL


def _quick_reply(prompt: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9\\s]", "", prompt.casefold()).strip()
    normalized = re.sub(r"\\s+", " ", normalized)
    return QUICK_REPLIES.get(normalized)


def handle_prompt(prompt: str) -> str:
    prompt = prompt.strip()
    if not prompt:
        return ""

    quick = _quick_reply(prompt)
    if quick:
        _remember(prompt, quick)
        return quick

    mission = _direct_mission(prompt)
    if mission is not None:
        return _execute_and_remember(prompt, mission)

    data, selected_model = _run_model_router(prompt)
    mode = data.get("mode")
    response = str(data.get("response", "")).strip()
    mission = data.get("mission", [])

    if mode == "mission":
        if not isinstance(mission, list) or not mission:
            raise ValueError("ULTRON selected mission mode without a mission.")

        results = execute(mission)
        failed = next((item for item in results if not item.get("ok")), None)

        if failed and selected_model != HEAVY_MODEL:
            repair_prompt = (
                prompt
                + "\n\nThe previous mission failed with this tool error:\n"
                + str(failed.get("error", "unknown error"))
                + "\nRepair the mission and return JSON only."
            )
            repaired, _ = _run_model_router(
                repair_prompt,
                forced_model=HEAVY_MODEL,
            )
            repaired_mission = repaired.get("mission", [])

            if isinstance(repaired_mission, list) and repaired_mission:
                mission = repaired_mission
                response = str(repaired.get("response", response)).strip()
                results = execute(mission)
                failed = next(
                    (item for item in results if not item.get("ok")),
                    None,
                )

        if failed:
            response = response or f"Mission stopped at step {failed.get('step')}."
            response += f" Error: {failed.get('error', 'unknown error')}."
        else:
            response = response or "Mission complete."

        _remember(prompt, response)
        return response

    if mode != "reply":
        raise ValueError(f"Unknown ULTRON mode: {mode!r}")

    _remember(prompt, response)
    return response


def _execute_and_remember(
    prompt: str,
    mission: list[dict[str, Any]],
    fallback: str = "",
) -> str:
    results = execute(mission)
    failed = next((item for item in results if not item.get("ok")), None)

    if failed:
        response = fallback or f"Mission stopped at step {failed.get('step')}."
        response += f" Error: {failed.get('error', 'unknown error')}."
    else:
        response = fallback or "Mission complete."

    _remember(prompt, response)
    return response


def _remember(prompt: str, response: str) -> None:
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    del history[:-40]
    _save()
