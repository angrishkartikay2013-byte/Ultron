from __future__ import annotations

import json
import inspect
import re
from typing import Any, Iterator, get_args, get_origin, get_type_hints

from .core import history, _save
from .llm import chat, stream_chat, resident_models, warm_model
from .router import AGENT_MODEL, FAST_MODEL, MID_MODEL, route_prompt
from debug import info
from tools.executor import execute
from tools.registry import discover, prompt_catalog


ROUTER_PROMPT = """You are ULTRON GENESIS, the user's local voice-first desktop AI assistant.

You are not a generic chatbot. You are the agency brain that decides whether the user's request is:
- ordinary conversation,
- a request for reasoning/help,
- a request to use the computer,
- a multi-step desktop mission,
- or genuinely ambiguous.

You receive natural-language speech transcriptions as well as typed requests. Speech may contain small transcription errors. Use the conversation context to resolve them when the intended meaning is clear.

Your capabilities are defined by the LIVE TOOL CATALOG supplied below. Treat that catalog as authoritative:
- If a suitable tool exists, use it instead of merely describing what the user could do.
- You may combine multiple tools and must preserve the user's requested sequence.
- Never invent a tool, argument, result, or completed action.
- Tool access is dynamic; do not assume aliases or hidden commands.
- When no tool is needed, answer naturally as ULTRON.

Return exactly one JSON object and no markdown.

Reply:
{"mode":"reply","response":"natural answer","mission":[]}

Mission:
{"mode":"mission","response":"brief draft for the eventual user-facing reply","mission":[
  {"tool":"<tool name>","arguments":{"<exact argument name>":"<value>"}}
]}

Rules:
- Use only tools from the supplied catalog.
- Use exact argument names and types.
- No extra argument names.
- Include every requested side effect.
- Preserve requested ordering for multiple actions.
- Do not claim that a mission succeeded before execution.
- Keep the response concise and human; do not mention internal JSON, routing, models, or prompts.
- If the request is genuinely ambiguous and the ambiguity changes what would be done, return an empty mission and ask one concise clarification.
"""

_OPERATOR_PROMPT = (
    ROUTER_PROMPT
    + "\n\nLIVE CAPABILITIES:\n"
    + "You can listen through the microphone, speak replies, inspect the Windows desktop when visual tools are available, and operate the computer through the supplied tools. "
    + "Do not claim any capability that is not represented by the live catalog.\n\nAVAILABLE TOOLS:\n"
)

RESULT_PROMPT = """You are ULTRON's final voice-response layer.

The user's request has already been processed by ULTRON's agency brain and the listed tools have now run.
Write the final natural response the user should hear.

Use ONLY the actual execution results supplied below.
Do not mention JSON, tool names, models, internal routing, prompts, or implementation details.
Do not invent success or failure.
If the requested action succeeded, confirm it naturally and briefly.
If something failed, state what actually failed and what happened before the failure.
Sound like a capable personal assistant, not a customer-service bot.
"""



def _json_type(annotation: Any) -> str:
    origin = get_origin(annotation)
    if origin in {list, tuple, set}:
        return "array"
    if origin is dict:
        return "object"
    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    if annotation is bool:
        return "boolean"
    return "string"


def _tool_argument_schema(spec: Any) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    try:
        hints = get_type_hints(spec.run)
    except Exception:
        hints = {}

    for name, parameter in inspect.signature(spec.run).parameters.items():
        if name in {"self", "cls"}:
            continue
        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue

        annotation = hints.get(name, parameter.annotation)
        if annotation is inspect._empty:
            annotation = str

        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin is not None and type(None) in args:
            non_none = [item for item in args if item is not type(None)]
            if non_none:
                properties[name] = {
                    "anyOf": [
                        {"type": _json_type(non_none[0])},
                        {"type": "null"},
                    ]
                }
            else:
                properties[name] = {}
        else:
            properties[name] = {"type": _json_type(annotation)}

        if parameter.default is inspect._empty:
            required.append(name)

    result: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        result["required"] = required
    return result


def _operator_schema() -> dict[str, Any]:
    variants: list[dict[str, Any]] = []

    for name, spec in sorted(discover().items()):
        variants.append({
            "type": "object",
            "properties": {
                "tool": {"type": "string", "enum": [name]},
                "arguments": _tool_argument_schema(spec),
            },
            "required": ["tool", "arguments"],
            "additionalProperties": False,
        })

    return {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["reply", "mission"]},
            "response": {"type": "string"},
            "mission": {
                "type": "array",
                "items": {"oneOf": variants},
            },
        },
        "required": ["mode", "response", "mission"],
        "additionalProperties": False,
    }


_OPERATOR_SCHEMA = _operator_schema()


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
    max_output_tokens: int = 256,
    history_turns: int = 5,
) -> tuple[dict[str, Any], str]:
    context = _model_context(history_turns) + [{"role": "user", "content": prompt}]

    def call_router(selected_model: str) -> dict[str, Any]:
        try:
            routed = chat(
                context,
                system_extra=_OPERATOR_PROMPT + prompt_catalog(),
                model=selected_model,
                max_output_tokens=max_output_tokens,
                num_ctx=2048,
                response_format=_OPERATOR_SCHEMA,
            )
            info(
                f"Agency raw output: model={selected_model} "
                f"{routed[:500]!r}"
            )
            data = _extract_json(routed)
        except Exception as exc:
            info(
                f"Agency attempt failed: model={selected_model} "
                f"error={exc}"
            )
            raise

        info(
            f"Agency JSON: model={selected_model} "
            f"mode={data.get('mode')!r} "
            f"mission_steps={len(data.get('mission', [])) if isinstance(data.get('mission'), list) else 'invalid'}"
        )
        return data

    try:
        data = call_router(model)
    except Exception:
        data = None

    if data is None:
        # Retry with the stronger configured fallback brain.
        info("Agency retry: switching to the fallback reasoning brain.")
        fallback = MID_MODEL if MID_MODEL != model else FAST_MODEL
        if fallback not in resident_models(refresh=True):
            info("Fallback reasoning brain is not resident; warming it.")
            warm_model(fallback)
        data = call_router(fallback)
        model = fallback

    mode = data.get("mode")
    mission = data.get("mission")
    response = data.get("response")

    if (
        mode not in {"reply", "mission"}
        or not isinstance(mission, list)
        or not isinstance(response, str)
    ):
        info("Agency JSON incomplete; retrying with the fallback reasoning brain.")
        fallback = MID_MODEL if MID_MODEL != model else FAST_MODEL
        if fallback not in resident_models(refresh=True):
            warm_model(fallback)
        data = call_router(fallback)
        model = fallback

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

    if route.agent == "agent":
        data, selected_model = _run_router(
            prompt,
            route.model,
            max_output_tokens=route.max_output_tokens,
            history_turns=route.history_turns,
        )
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
                    max_output_tokens=256,
                    num_ctx=2048,
                    response_format=_OPERATOR_SCHEMA,
                )
                repaired_data = _extract_json(repaired)
                repaired_mission = repaired_data.get("mission", [])
                info(
                    f"Agency repair JSON: mode={repaired_data.get('mode')!r} "
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

            execution_text = json.dumps(
                results,
                ensure_ascii=False,
                indent=2,
            )

            finalizer_context = _model_context(2) + [
                {"role": "user", "content": prompt},
                {
                    "role": "assistant",
                    "content": response or "Mission planned.",
                },
                {
                    "role": "user",
                    "content": (
                        "ACTUAL EXECUTION RESULTS:\n"
                        + execution_text
                    ),
                },
            ]

            final_response = chat(
                finalizer_context,
                system_extra=RESULT_PROMPT,
                model=FAST_MODEL,
                max_output_tokens=96,
                num_ctx=1024,
            ).strip()

            if not final_response:
                if failed:
                    final_response = (
                        f"Step {failed.get('step')} failed: "
                        f"{failed.get('error', 'unknown error')}."
                    )
                else:
                    final_response = response or "Done."

            info(
                f"Mission executed: steps={len(mission)} "
                f"result={'failed' if failed else 'success'}"
            )
            _remember(prompt, final_response)
            return final_response

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

    if route.agent == "agent":
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
