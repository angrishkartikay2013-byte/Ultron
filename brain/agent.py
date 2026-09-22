from __future__ import annotations

import json
import re
from typing import Any, Iterator

from .cache import response_cache
from .core import history, _save
from .llm import chat, stream_chat
from .router import AGENT_MODEL, MID_MODEL, route_prompt
from tools.executor import execute
from tools.registry import prompt_catalog


ROUTER_PROMPT = """You are ULTRON's desktop operator.
Speech recognition can contain small transcription errors.
Infer the intended command silently.
Return exactly one JSON object and no markdown.

Reply:
{"mode":"reply","response":"short response","mission":[]}

Mission:
{"mode":"mission","response":"short status","mission":[
  {"tool":"<tool name>","arguments":{"<argument>":"<value>"}}
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
    # Mission planning is model-driven. Keep this layer free of hard-coded
    # natural-language command patterns.
    return None


def _model_context(turns: int) -> list[dict[str, str]]:
    return list(history[-turns * 2:])


def _run_router(
    prompt: str,
    model: str,
    max_output_tokens: int = 64,
) -> tuple[dict[str, Any], str]:
    context = _model_context(1) + [{"role": "user", "content": prompt}]
    routed = chat(
        context,
        system_extra=_OPERATOR_PROMPT + prompt_catalog(),
        model=model,
        max_output_tokens=max_output_tokens,
        num_ctx=640,
        response_format="json",
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
        data, selected_model = _run_router(prompt, route.model)
        mode = data.get("mode")
        response = str(data.get("response", "")).strip()
        mission = data.get("mission", [])

        if mode == "mission":
            if not isinstance(mission, list) or not mission:
                raise ValueError("Operator returned no mission.")

            results = execute(mission)
            failed = next((item for item in results if not item.get("ok")), None)

            if failed:
                # Repair only when necessary.
                repair_context = _model_context(1) + [{
                    "role": "user",
                    "content": (
                        prompt
                        + "\nRepair the failed mission. Tool error: "
                        + str(failed.get("error", "unknown error"))
                    ),
                }]
                repaired = chat(
                    repair_context,
                    system_extra=_OPERATOR_PROMPT + prompt_catalog(),
                    model=MID_MODEL,
                    max_output_tokens=96,
                    num_ctx=768,
                    response_format="json",
                )
                repaired_data = _extract_json(repaired)
                repaired_mission = repaired_data.get("mission", [])
                if isinstance(repaired_mission, list) and repaired_mission:
                    mission = repaired_mission
                    response = str(
                        repaired_data.get("response", response)
                    ).strip()
                    results = execute(mission)
                    failed = next(
                        (item for item in results if not item.get("ok")),
                        None,
                    )

            if failed:
                response = response or "The mission failed."
                response += (
                    f" Step {failed.get('step')} failed: "
                    f"{failed.get('error', 'unknown error')}."
                )
            else:
                response = response or "Mission completed."

            _remember(prompt, response)
            return response

        if mode != "reply":
            raise ValueError(f"Unknown ULTRON mode: {mode!r}")

        response_cache.put(prompt, response)
        _remember(prompt, response)
        return response

    context = (
        _model_context(route.history_turns)
        if route.history_turns > 0
        else []
    ) + [{"role": "user", "content": prompt}]
    response = chat(
        context,
        model=route.model,
        max_output_tokens=route.max_output_tokens,
        num_ctx=route.num_ctx,
    )
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

    context = (
        _model_context(route.history_turns)
        if route.history_turns > 0
        else []
    ) + [{"role": "user", "content": prompt}]
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
        # Do not immediately run a second full model call: that doubles
        # latency after a transient streaming failure.
        if parts:
            return
        raise

    final = "".join(parts).strip()
    if final:
        response_cache.put(prompt, final)
        _remember(prompt, final)
