from __future__ import annotations

import json
import re
from typing import Any, Iterator

from .core import history, _save
from .llm import chat, stream_chat, resident_models, warm_model
from .router import AGENT_MODEL, FAST_MODEL, MID_MODEL, route_prompt
from debug import info
from tools.executor import execute
from tools.registry import prompt_catalog


ROUTER_PROMPT = """You are ULTRON's desktop operator.
You translate a user's natural-language request into safe actions using only the supplied tool catalog.
Speech recognition may contain small transcription errors. Use the conversation context to infer the most plausible intended wording, but never invent a task the user did not request.
Return exactly one JSON object and no markdown.

Reply:
{"mode":"reply","response":"brief natural reply","mission":[]}

Mission:
{"mode":"mission","response":"brief natural status","mission":[
  {"tool":"<tool name>","arguments":{"<exact argument name>":"<value>"}}
]}

Rules:
- Use only tools from the catalog.
- Use the exact argument names and required argument types from the catalog.
- Never add extra argument names.
- Preserve the user's requested sequence when multiple actions are requested.
- Include every requested side effect; do not silently drop steps.
- Keep the response natural and specific to what was actually requested.
- Do not output placeholders such as "short response".
- If the request is genuinely ambiguous, use an empty mission and ask one concise clarification.
"""

_OPERATOR_PROMPT = ROUTER_PROMPT + "\n\nAVAILABLE TOOLS:\n"

_OPERATOR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "mode": {"type": "string", "enum": ["reply", "mission"]},
        "response": {"type": "string"},
        "mission": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "arguments": {"type": "object"},
                },
                "required": ["tool", "arguments"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["mode", "response", "mission"],
    "additionalProperties": False,
}


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
    max_output_tokens: int = 128,
) -> tuple[dict[str, Any], str]:
    context = _model_context(1) + [{"role": "user", "content": prompt}]

    def call_router(selected_model: str) -> dict[str, Any]:
        try:
            routed = chat(
                context,
                system_extra=_OPERATOR_PROMPT + prompt_catalog(),
                model=selected_model,
                max_output_tokens=max_output_tokens,
                num_ctx=768,
                response_format=_OPERATOR_SCHEMA,
            )
            info(
                f"Operator raw output: model={selected_model} "
                f"{routed[:500]!r}"
            )
            data = _extract_json(routed)
        except Exception as exc:
            info(
                f"Operator attempt failed: model={selected_model} "
                f"error={exc}"
            )
            raise

        info(
            f"Operator JSON: model={selected_model} "
            f"mode={data.get('mode')!r} "
            f"mission_steps={len(data.get('mission', [])) if isinstance(data.get('mission'), list) else 'invalid'}"
        )
        return data

    try:
        data = call_router(model)
    except Exception:
        data = None

    if data is None:
        # Retry with the 3B reasoning brain after an operator failure.
        info("Operator retry: switching to the reasoning brain.")
        if MID_MODEL not in resident_models(refresh=True):
            info("Reasoning brain is not resident; warming it for operator retry.")
            warm_model(MID_MODEL)
        data = call_router(MID_MODEL)
        model = MID_MODEL

    mode = data.get("mode")
    mission = data.get("mission")
    response = data.get("response")

    if (
        mode not in {"reply", "mission"}
        or not isinstance(mission, list)
        or not isinstance(response, str)
    ):
        info("Operator JSON incomplete; retrying with the reasoning brain.")
        if MID_MODEL not in resident_models(refresh=True):
            warm_model(MID_MODEL)
        data = call_router(MID_MODEL)
        model = MID_MODEL

    return data, model


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

    route = route_prompt(prompt)

    if route.agent == "operator":
        data, selected_model = _run_router(prompt, route.model)
        mode = data.get("mode")
        response = str(data.get("response", "")).strip()
        mission = data.get("mission", [])

        # A structured mission is authoritative regardless of the model's
        # mode label. Small local models sometimes return a valid mission
        # while incorrectly labeling the envelope as "reply".
        if isinstance(mission, list) and mission:
            results = execute(mission)
            failed = next((item for item in results if not item.get("ok")), None)

            if failed:
                info(
                    f"Mission execution failed: step={failed.get('step')} "
                    f"tool={failed.get('tool')} error={failed.get('error')}"
                )
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
                    max_output_tokens=128,
                    num_ctx=768,
                    response_format=_OPERATOR_SCHEMA,
                )
                repaired_data = _extract_json(repaired)
                repaired_mission = repaired_data.get("mission", [])
                info(
                    f"Operator repair JSON: mode={repaired_data.get('mode')!r} "
                    f"mission_steps={len(repaired_mission) if isinstance(repaired_mission, list) else 'invalid'}"
                )
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

            info(
                f"Mission executed: steps={len(mission)} "
                f"result={'failed' if failed else 'success'}"
            )
            _remember(prompt, response)
            return response

        if mode == "reply":
            _remember(prompt, response)
            return response

        if mode == "mission":
            raise ValueError("Operator requested a mission but returned no mission.")

        raise ValueError(f"Unknown ULTRON mode: {mode!r}")

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
        _remember(prompt, final)
