from __future__ import annotations

import json
import re
from typing import Any, Iterator

from .cache import response_cache
from .core import history, _save
from .llm import chat, stream_chat
from .router import AGENT_MODEL, FAST_MODEL, MID_MODEL, HEAVY_MODEL, route_prompt
from tools.executor import execute
from tools.registry import prompt_catalog


ROUTER_PROMPT = """You are ULTRON's desktop operator.
Input may be speech-recognized and contain obvious grammar, spelling, or transcription mistakes. Silently infer the intended command before routing it.
Return exactly one JSON object and no markdown.

Reply:
{"mode":"reply","response":"short response","mission":[]}

Mission:
{"mode":"mission","response":"short status","mission":[
  {"tool":"open_app","arguments":{"app":"notepad"}}
]}

Rules:
- Only use available tools.
- Use exact argument names.
- Never invent tools.
- Keep the mission minimal.
"""

_OPERATOR_PROMPT = ROUTER_PROMPT + "\n\nAVAILABLE TOOLS:\n"


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
            {"tool": "wait", "arguments": {"seconds": 0.7}},
            {"tool": "type_text", "arguments": {"text": value}},
        ]

    match = re.match(r"^(?:open|launch|start)\s+(.+)$", text, flags=re.I)
    if match and len(text.split()) <= 8:
        return [{"tool": "open_app", "arguments": {"app": match.group(1).strip(" .")}}]

    match = re.match(
        r"^(?:move|put)\s+(?:the\s+)?mouse\s+(?:to|at)\s+(.+)$",
        text,
        flags=re.I,
    )
    if match:
        position = match.group(1).strip(" .")
        coordinate = re.match(r"^\(?\s*(\d+)\s*[, ]\s*(\d+)\s*\)?$", position)
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


def _model_context() -> list[dict[str, str]]:
    return list(history[-8:])


def _run_router(prompt: str, model: str, max_output_tokens: int = 180) -> tuple[dict[str, Any], str]:
    context = _model_context() + [{"role": "user", "content": prompt}]
    routed = chat(
        context,
        system_extra=_OPERATOR_PROMPT + prompt_catalog(),
        model=model,
        max_output_tokens=max_output_tokens,
        num_ctx=1024,
    )
    return _extract_json(routed), model


def _execute_mission(
    prompt: str,
    mission: list[dict[str, Any]],
    response: str = "",
) -> str:
    results = execute(mission)
    failed = next((item for item in results if not item.get("ok")), None)

    if failed:
        output = response or "The mission could not be completed."
        output += f" Step {failed.get('step')} failed: {failed.get('error', 'unknown error')}."
    else:
        output = response or "Mission completed."

    _remember(prompt, output)
    return output


def _remember(prompt: str, response: str) -> None:
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    del history[:-40]
    _save()


def handle_prompt(prompt: str) -> str:
    prompt = prompt.strip()
    if not prompt:
        return ""

    mission = _direct_mission(prompt)
    if mission is not None:
        return _execute_mission(prompt, mission)

    cached = response_cache.get(prompt)
    if cached is not None:
        _remember(prompt, cached)
        return cached

    route = route_prompt(prompt)

    if route.agent == "operator":
        try:
            data, selected_model = _run_router(prompt, AGENT_MODEL, 96)
        except Exception:
            data, selected_model = _run_router(prompt, FAST_MODEL, 160)
    else:
        context = _model_context() + [{"role": "user", "content": prompt}]
        response = chat(
            context,
            model=route.model,
            max_output_tokens=route.max_output_tokens,
            num_ctx=route.num_ctx,
        )
        response_cache.put(prompt, response)
        _remember(prompt, response)
        return response

    mode = data.get("mode")
    response = str(data.get("response", "")).strip()
    mission = data.get("mission", [])

    if mode == "mission":
        if not isinstance(mission, list) or not mission:
            raise ValueError("Operator agent selected mission mode without a mission.")

        results = execute(mission)
        failed = next((item for item in results if not item.get("ok")), None)

        if failed and selected_model != MID_MODEL:
            repaired, _ = _run_router(
                prompt
                + "\n\nRepair the previous mission using this tool error:\n"
                + str(failed.get("error", "unknown error")),
                MID_MODEL,
                180,
            )
            repaired_mission = repaired.get("mission", [])
            if isinstance(repaired_mission, list) and repaired_mission:
                mission = repaired_mission
                response = str(repaired.get("response", response)).strip()
                results = execute(mission)
                failed = next((item for item in results if not item.get("ok")), None)

        if failed:
            response = response or "The mission failed."
            response += f" Step {failed.get('step')} failed: {failed.get('error', 'unknown error')}."
        else:
            response = response or "Mission completed."

        _remember(prompt, response)
        return response

    if mode != "reply":
        raise ValueError(f"Unknown ULTRON mode: {mode!r}")

    response_cache.put(prompt, response)
    _remember(prompt, response)
    return response


def stream_prompt(prompt: str) -> Iterator[str]:
    prompt = prompt.strip()
    if not prompt:
        return

    mission = _direct_mission(prompt)
    if mission is not None:
        yield _execute_mission(prompt, mission)
        return

    cached = response_cache.get(prompt)
    if cached is not None:
        _remember(prompt, cached)
        yield cached
        return

    route = route_prompt(prompt)

    if route.agent == "operator":
        yield handle_prompt(prompt)
        return

    context = _model_context() + [{"role": "user", "content": prompt}]
    parts: list[str] = []

    try:
        for token in stream_chat(
            context,
            model=route.model,
            max_output_tokens=route.max_output_tokens,
            num_ctx=route.num_ctx,
        ):
            parts.append(token)
            yield token
    except Exception:
        fallback = handle_prompt(prompt)
        yield fallback
        return

    final = "".join(parts).strip()
    if final:
        response_cache.put(prompt, final)
        _remember(prompt, final)
