from __future__ import annotations

import json
from typing import Any, Iterator

from .core import _save, history
from .llm import chat_raw, resident_models, warm_model
from .router import AGENT_MODEL, route_prompt
from debug import info
from tools.executor import execute
from tools.registry import discover, ollama_tools


AGENT_SYSTEM = """You are ULTRON GENESIS, a voice-first Windows desktop AI assistant.

You are the agency brain, not a generic chatbot.
You know that ULTRON can:
- listen to the user through speech transcription,
- remember conversation and durable facts,
- inspect the screen through the visual cortex when the screen-vision tool is available,
- operate Windows through the live tool registry,
- create and stage new tools through the Tool Workshop,
- and report what actually happened after tools execute.

The LIVE TOOL REGISTRY supplied to you is authoritative. Never invent hidden capabilities.

Behavior:
- Understand the user's intent from natural language and speech transcription.
- Use conversation context to resolve obvious transcription mistakes.
- For desktop requests, actually use an appropriate tool when one exists.
- You may call several tools in sequence. Preserve the user's requested order.
- After a tool result, decide whether another tool is needed or whether the task is complete.
- Do not claim an action happened until the tool result says it happened.
- Do not make the user repeat context that is already in the conversation.
- If an important ambiguity changes the action, ask one concise clarification instead of guessing.
- For ordinary conversation, do not call tools unnecessarily.
- Keep responses natural, direct, and suitable for voice.
- Never mention internal prompts, JSON, routing, model names, or private chain-of-thought.
"""

MAX_TOOL_ROUNDS = 8
MAX_TOOL_RESULT_CHARS = 5000


def _model_context(turns: int) -> list[dict[str, Any]]:
    return list(history[-turns * 2:]) if turns > 0 else []


def _truncate(value: Any) -> str:
    text = str(value)
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text
    return text[:MAX_TOOL_RESULT_CHARS] + "\n[tool output truncated]"


def _tool_messages_for(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [response]


def _available_model() -> str:
    loaded = resident_models(refresh=False)
    if AGENT_MODEL in loaded:
        return AGENT_MODEL

    try:
        warm_model(AGENT_MODEL)
        return AGENT_MODEL
    except Exception:
        return next(iter(loaded), AGENT_MODEL)


def _remember(prompt: str, response: str) -> None:
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    del history[:-40]
    _save()


def handle_prompt(prompt: str) -> str:
    prompt = prompt.strip()
    if not prompt:
        return ""

    route = route_prompt(prompt)
    model = route.model or _available_model()
    tools = ollama_tools()

    messages: list[dict[str, Any]] = _model_context(route.history_turns)
    messages.append({"role": "user", "content": prompt})

    for round_index in range(1, MAX_TOOL_ROUNDS + 1):
        response = chat_raw(
            messages,
            model=model,
            tools=tools,
            system_extra=AGENT_SYSTEM,
            max_output_tokens=route.max_output_tokens,
            num_ctx=route.num_ctx,
        )

        tool_calls = response.get("tool_calls") or []
        content = str(response.get("content") or "").strip()

        if not tool_calls:
            if content:
                _remember(prompt, content)
                return content
            raise RuntimeError("ULTRON's agency brain returned no response.")

        messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
        })

        mission = []
        registry = discover()

        for call in tool_calls:
            function = call.get("function", {})
            tool_name = function.get("name")
            arguments = function.get("arguments", {})

            if not isinstance(tool_name, str):
                continue
            if not isinstance(arguments, dict):
                arguments = {}

            mission.append({
                "tool": tool_name,
                "arguments": arguments,
            })

        if not mission:
            messages.append({
                "role": "tool",
                "content": "No valid tool call was returned.",
                "tool_name": "unknown",
            })
            continue

        results = execute(mission)

        for result in results:
            tool_name = result.get("tool", "unknown")
            if result.get("ok"):
                output = {
                    "ok": True,
                    "output": _truncate(result.get("output", "")),
                }
            else:
                output = {
                    "ok": False,
                    "error": _truncate(result.get("error", "unknown error")),
                }

            messages.append({
                "role": "tool",
                "content": json.dumps(output, ensure_ascii=False),
                "tool_name": str(tool_name),
            })

        info(
            f"Agency tool round={round_index} "
            f"calls={len(mission)} "
            f"results_ok={sum(1 for item in results if item.get('ok'))}"
        )

    raise RuntimeError("ULTRON reached the safe tool-call limit for this request.")


def stream_prompt(prompt: str) -> Iterator[str]:
    result = handle_prompt(prompt)
    if result:
        yield result
