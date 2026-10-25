from __future__ import annotations

import base64
import json
import os
import subprocess
import threading
import time
from typing import Any, Iterator

import requests

from .router import AGENT_MODEL, FAST_MODEL, HEAVY_MODEL, MID_MODEL, MICRO_MODEL, VISION_MODEL

BASE_URL = os.getenv("ULTRON_OLLAMA_URL", "http://127.0.0.1:11434")
URL = f"{BASE_URL}/api/chat"
OLLAMA_MODELS = os.getenv("OLLAMA_MODELS", r"E:\ULTRON\models")
OLLAMA_EXE = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
CPU_THREADS = int(os.getenv("ULTRON_CPU_THREADS", str(max(2, min(4, os.cpu_count() or 4)))))

SYSTEM_PROMPT = """You are ULTRON, a local voice-first personal desktop AI assistant.
You are part of a larger agent system. Speak naturally, confidently, and conversationally, like a sharp human assistant.
Treat the conversation as continuous; remember names, topics, prior decisions, and what the user just said.
You may receive speech transcriptions, typed text, or results from desktop tools. Treat each as context, not as a canned command syntax.
Do not repeat greetings, restate the prompt, or use canned customer-service phrases.
Answer the actual question first. Add detail only when useful.
For casual conversation, sound relaxed and human rather than formal.
For technical questions, be precise and practical.
For desktop tasks, only claim an action occurred when the supplied execution results support it.
For ambiguous speech, use context to infer the most plausible interpretation; ask one concise question only when the ambiguity materially changes the answer.
Never invent facts, actions, tool results, or capabilities.
Never reveal private chain-of-thought.
"""
REFLEX_SYSTEM_PROMPT = """You are ULTRON.
Be natural, direct, conversational, and useful.
Use prior context when available.
Avoid canned openings and repetitive apologies.
If the user's meaning is genuinely ambiguous, ask one short question instead of guessing.
"""

_SESSION = requests.Session()
_OLLAMA_READY = False
_INSTALLED_MODELS: set[str] | None = None
_LOADED_MODELS: tuple[set[str], float] | None = None
_LOADED_LOCK = threading.Lock()
RESIDENT_CACHE_TTL = 5.0


def ensure_ollama() -> None:
    global _OLLAMA_READY

    if _OLLAMA_READY:
        return

    try:
        _SESSION.get(f"{BASE_URL}/api/tags", timeout=1.0)
        _OLLAMA_READY = True
        return
    except requests.RequestException:
        pass

    env = os.environ.copy()
    env["OLLAMA_MODELS"] = OLLAMA_MODELS

    subprocess.Popen(
        [OLLAMA_EXE, "serve"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    for _ in range(30):
        try:
            _SESSION.get(f"{BASE_URL}/api/tags", timeout=0.7)
            _OLLAMA_READY = True
            return
        except requests.RequestException:
            time.sleep(0.25)

    raise RuntimeError("Ollama did not become available on 127.0.0.1:11434")


def installed_models(refresh: bool = False) -> set[str]:
    global _INSTALLED_MODELS

    ensure_ollama()
    if _INSTALLED_MODELS is not None and not refresh:
        return _INSTALLED_MODELS

    response = _SESSION.get(f"{BASE_URL}/api/tags", timeout=4)
    response.raise_for_status()
    _INSTALLED_MODELS = {
        item.get("name", "")
        for item in response.json().get("models", [])
        if item.get("name")
    }
    return _INSTALLED_MODELS

def resident_models(refresh: bool = False) -> set[str]:
    """Return models currently resident in Ollama memory, not merely installed."""
    global _LOADED_MODELS

    ensure_ollama()
    now = time.monotonic()

    with _LOADED_LOCK:
        if _LOADED_MODELS is not None and not refresh:
            models, timestamp = _LOADED_MODELS
            if now - timestamp < RESIDENT_CACHE_TTL:
                return set(models)

        response = _SESSION.get(f"{BASE_URL}/api/ps", timeout=2)
        response.raise_for_status()
        models = {
            item.get("name") or item.get("model", "")
            for item in response.json().get("models", [])
            if item.get("name") or item.get("model")
        }
        _LOADED_MODELS = (models, now)
        return set(models)



def choose_ready_model(preferred: str) -> str:
    """Choose only a resident model; never cause a cold model load."""
    loaded = resident_models(refresh=False)

    priorities = {
        HEAVY_MODEL: (HEAVY_MODEL, MID_MODEL, FAST_MODEL, AGENT_MODEL),
        MID_MODEL: (MID_MODEL, FAST_MODEL, AGENT_MODEL),
        FAST_MODEL: (FAST_MODEL, AGENT_MODEL),
        AGENT_MODEL: (AGENT_MODEL, FAST_MODEL),
        VISION_MODEL: (VISION_MODEL,),
        MICRO_MODEL: (MICRO_MODEL, AGENT_MODEL),
    }

    for candidate in priorities.get(preferred, (preferred, FAST_MODEL, AGENT_MODEL)):
        if candidate in loaded:
            return candidate

    for candidate in (MICRO_MODEL, AGENT_MODEL, FAST_MODEL, MID_MODEL, HEAVY_MODEL):
        if candidate in loaded:
            return candidate

    raise RuntimeError("No resident language model is available yet.")

def resident_model_for(preferred: str) -> str:
    return choose_ready_model(preferred)


def choose_model(preferred: str) -> str:
    models = installed_models()

    if preferred in models:
        return preferred

    if preferred == MICRO_MODEL:
        if AGENT_MODEL in models:
            return AGENT_MODEL
        if FAST_MODEL in models:
            return FAST_MODEL

    if preferred == AGENT_MODEL and FAST_MODEL in models:
        return FAST_MODEL

    if preferred == HEAVY_MODEL and MID_MODEL in models:
        return MID_MODEL

    if preferred == MID_MODEL and FAST_MODEL in models:
        return FAST_MODEL

    if preferred == FAST_MODEL and models:
        for candidate in (FAST_MODEL, MID_MODEL, HEAVY_MODEL):
            if candidate in models:
                return candidate

    if models:
        return sorted(models)[0]

    raise RuntimeError("No Ollama models are installed.")
def _payload_options(
    model: str,
    max_output_tokens: int,
    num_ctx: int,
    *,
    structured: bool = False,
) -> dict[str, Any]:
    if model == HEAVY_MODEL:
        return {
            "temperature": 0.12 if structured else 0.28,
            "top_p": 0.88 if structured else 0.92,
            "top_k": 24 if structured else 40,
            "num_ctx": num_ctx,
            "num_predict": max_output_tokens,
            "num_thread": CPU_THREADS,
            "num_batch": 128,
            "num_gpu": 0,
        }

    return {
        "temperature": 0.05 if structured else 0.32,
        "top_p": 0.90 if structured else 0.92,
        "top_k": 24 if structured else 40,
        "num_ctx": num_ctx,
        "num_predict": max_output_tokens,
        "num_thread": CPU_THREADS,
        "num_batch": 128,
        "num_gpu": 0,
    }


def _keep_alive(model: str) -> str:
    if model in {MICRO_MODEL, AGENT_MODEL, FAST_MODEL}:
        return "90m"
    if model == MID_MODEL:
        return "15m"
    return "10m"


def _effective_limits(
    model: str,
    max_output_tokens: int,
    num_ctx: int,
) -> tuple[int, int]:
    limits = {
        MICRO_MODEL: (24, 128),
        AGENT_MODEL: (96, 768),
        FAST_MODEL: (160, 1024),
        MID_MODEL: (224, 2048),
        HEAVY_MODEL: (256, 4096),
        VISION_MODEL: (128, 768),
    }
    output_cap, ctx_cap = limits.get(model, (72, 768))
    return min(max_output_tokens, output_cap), min(num_ctx, ctx_cap)


def warm_model(model: str = FAST_MODEL) -> str:
    selected = choose_model(model)
    response = _SESSION.post(
        URL,
        json={
            "model": selected,
            "messages": [{"role": "user", "content": "Ready."}],
            "stream": False,
            "think": False,
            "keep_alive": _keep_alive(selected),
            "options": _payload_options(selected, 1, 384),
        },
        timeout=120,
    )
    response.raise_for_status()
    with _LOADED_LOCK:
        global _LOADED_MODELS
        _LOADED_MODELS = None
    return selected


def warm_speed_stack() -> tuple[str, str]:
    # Keep the stronger 1.5B conversational/operator brain warm, plus the 3B
    # reasoning brain for deeper turns.
    fast = warm_model(FAST_MODEL)
    reasoning = warm_model(MID_MODEL)
    return fast, reasoning


def _messages(
    history: list[dict[str, Any]],
    system: str,
) -> list[dict[str, Any]]:
    return [{"role": "system", "content": system}, *history]


def vision_chat(
    prompt: str,
    image_bytes: bytes,
    timeout: int = 90,
    max_output_tokens: int = 128,
    response_format: str | dict[str, Any] | None = None,
) -> str:
    selected_model = choose_model(VISION_MODEL) if VISION_MODEL in installed_models() else VISION_MODEL
    if selected_model not in installed_models():
        raise RuntimeError(
            f"Vision model {VISION_MODEL!r} is not installed. "
            "Run: uv run scripts/setup_fast_model.py"
        )

    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are ULTRON's visual cortex. Inspect the supplied Windows "
                "screenshot accurately. Never claim to see something that is not "
                "visible. Return only what the image supports."
            ),
        },
        {
            "role": "user",
            "content": prompt,
            "images": [image_b64],
        },
    ]

    payload = {
        "model": selected_model,
        "messages": messages,
        "stream": False,
        "think": False,
        "keep_alive": "5m",
        "options": _payload_options(
            selected_model,
            *_effective_limits(selected_model, max_output_tokens, 768),
        ),
    }

    if response_format:
        payload["format"] = response_format

    response = _SESSION.post(URL, json=payload, timeout=timeout)
    response.raise_for_status()

    content = response.json().get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError("Vision model returned an invalid response.")
    return content.strip()


def chat(
    history: list[dict[str, str]],
    timeout: int = 60,
    system_extra: str = "",
    model: str | None = None,
    max_output_tokens: int = 72,
    num_ctx: int = 768,
    response_format: str | dict[str, Any] | None = None,
) -> str:
    selected_model = choose_ready_model(model or FAST_MODEL)
    effective_output, effective_ctx = _effective_limits(
        selected_model, max_output_tokens, num_ctx
    )
    system = (
        REFLEX_SYSTEM_PROMPT
        if selected_model in {MICRO_MODEL, AGENT_MODEL} and not system_extra.strip()
        else SYSTEM_PROMPT
    )
    if system_extra.strip():
        system += "\n\n" + system_extra.strip()

    payload = {
        "model": selected_model,
        "messages": _messages(history, system),
        "stream": False,
        "think": selected_model in {AGENT_MODEL, HEAVY_MODEL},
        "keep_alive": _keep_alive(selected_model),
        "options": _payload_options(
            selected_model,
            effective_output,
            effective_ctx,
            structured=bool(response_format or system_extra.strip()),
        ),
    }
    if response_format:
        payload["format"] = response_format

    response = _SESSION.post(URL, json=payload, timeout=timeout)
    response.raise_for_status()

    content = response.json().get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError("Ollama returned an invalid response.")
    return content.strip()


def stream_chat(
    history: list[dict[str, str]],
    timeout: int = 60,
    system_extra: str = "",
    model: str | None = None,
    max_output_tokens: int = 72,
    num_ctx: int = 768,
) -> Iterator[str]:
    selected_model = choose_ready_model(model or FAST_MODEL)
    effective_output, effective_ctx = _effective_limits(
        selected_model, max_output_tokens, num_ctx
    )
    system = (
        REFLEX_SYSTEM_PROMPT
        if selected_model in {MICRO_MODEL, AGENT_MODEL} and not system_extra.strip()
        else SYSTEM_PROMPT
    )
    if system_extra.strip():
        system += "\n\n" + system_extra.strip()

    response = _SESSION.post(
        URL,
        json={
            "model": selected_model,
            "messages": _messages(history, system),
            "stream": True,
            "think": False,
            "keep_alive": _keep_alive(selected_model),
            "options": _payload_options(
                selected_model,
                effective_output,
                effective_ctx,
                structured=bool(system_extra.strip()),
            ),
        },
        timeout=(1.5, timeout),
        stream=True,
    )
    response.raise_for_status()

    try:
        for line in response.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            if data.get("done"):
                break

            token = data.get("message", {}).get("content")
            if isinstance(token, str) and token:
                yield token
    finally:
        response.close()


def provider_status() -> str:
    """Describe the agent provider selected by environment variables."""
    provider = os.getenv("ULTRON_PROVIDER", "auto").strip().lower()
    key_present = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    if provider == "auto":
        return "OpenRouter (configured)" if key_present else "Ollama (local fallback)"
    if provider == "openrouter":
        return "OpenRouter (configured)" if key_present else "OpenRouter (API key missing)"
    if provider in {"ollama", "local"}:
        return "Ollama (local)"
    return f"Unknown provider setting: {provider}"


def _selected_agent_provider() -> str:
    provider = os.getenv("ULTRON_PROVIDER", "auto").strip().lower()
    if provider == "auto":
        return "openrouter" if os.getenv("OPENROUTER_API_KEY", "").strip() else "ollama"
    if provider in {"ollama", "local"}:
        return "ollama"
    if provider == "openrouter":
        if not os.getenv("OPENROUTER_API_KEY", "").strip():
            raise RuntimeError(
                "ULTRON_PROVIDER is set to openrouter, but OPENROUTER_API_KEY is not set. "
                "Add the key to your Windows user environment variables and restart ULTRON."
            )
        return "openrouter"
    raise RuntimeError(
        f"Unknown ULTRON_PROVIDER={provider!r}. Choose auto, openrouter, or ollama."
    )


def _openrouter_messages(
    messages: list[dict[str, Any]],
    system: str,
) -> list[dict[str, Any]]:
    """Translate the agent loop's Ollama-shaped messages into OpenAI-compatible messages."""
    result: list[dict[str, Any]] = [{"role": "system", "content": system}]
    pending_calls: dict[str, list[str]] = {}
    synthetic_counter = 0

    for message in messages:
        role = str(message.get("role") or "user")
        content = message.get("content", "")

        if role == "assistant" and message.get("tool_calls"):
            converted_calls: list[dict[str, Any]] = []
            for call in message.get("tool_calls") or []:
                function = call.get("function") or {}
                name = str(function.get("name") or "unknown")
                arguments = function.get("arguments", {})
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                if not isinstance(arguments, dict):
                    arguments = {}
                call_id = str(call.get("id") or f"ultron_call_{len(result)}_{len(converted_calls)}")
                pending_calls.setdefault(name, []).append(call_id)
                converted_calls.append({
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(arguments, ensure_ascii=False),
                    },
                })
            result.append({
                "role": "assistant",
                "content": content or None,
                "tool_calls": converted_calls,
            })
            continue

        if role == "tool":
            name = str(message.get("tool_name") or message.get("name") or "unknown")
            call_id = message.get("tool_call_id")
            if not call_id:
                candidates = pending_calls.get(name, [])
                if candidates:
                    call_id = candidates.pop(0)
                else:
                    synthetic_counter += 1
                    call_id = f"ultron_tool_result_{synthetic_counter}"
            result.append({
                "role": "tool",
                "tool_call_id": str(call_id),
                "name": name,
                "content": str(content),
            })
            continue

        if role in {"user", "assistant", "system"}:
            result.append({"role": role, "content": content})
        else:
            result.append({"role": "user", "content": str(content)})

    return result


def _openrouter_chat_raw(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None,
    timeout: int,
    system_extra: str,
    max_output_tokens: int,
    num_ctx: int,
) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

    selected_model = os.getenv("ULTRON_OPENROUTER_MODEL", "openrouter/free").strip()
    if not selected_model:
        selected_model = "openrouter/free"

    system = SYSTEM_PROMPT
    if system_extra.strip():
        system += "\n\n" + system_extra.strip()

    payload: dict[str, Any] = {
        "model": selected_model,
        "messages": _openrouter_messages(messages, system),
        "max_tokens": max(1, int(max_output_tokens)),
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "ULTRON",
    }
    response = _SESSION.post(
        os.getenv("ULTRON_OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions"),
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        # Avoid echoing request headers or the secret key in any error text.
        body = response.text[:1200]
        raise RuntimeError(
            f"OpenRouter request failed ({response.status_code}). "
            f"Check the API key, model availability and free-tier limits. Details: {body}"
        ) from exc

    body = response.json()
    choices = body.get("choices") or []
    if not choices or not isinstance(choices[0].get("message"), dict):
        raise RuntimeError("OpenRouter returned no chat message.")

    remote_message = choices[0]["message"]
    normalized_calls: list[dict[str, Any]] = []
    for call in remote_message.get("tool_calls") or []:
        function = call.get("function") or {}
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        normalized_calls.append({
            "id": str(call.get("id") or f"ultron_call_{len(normalized_calls)}"),
            "type": "function",
            "function": {
                "name": str(function.get("name") or "unknown"),
                "arguments": arguments,
            },
        })

    usage = body.get("usage") or {}
    try:
        from runtime.token_state import update as update_token_state
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
        update_token_state(
            model=str(body.get("model") or selected_model),
            context_limit=max(0, int(num_ctx)),
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
        )
    except (ImportError, TypeError, ValueError):
        pass

    return {
        "role": "assistant",
        "content": str(remote_message.get("content") or ""),
        "tool_calls": normalized_calls,
    }


def chat_raw(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    timeout: int = 120,
    system_extra: str = "",
    max_output_tokens: int = 256,
    num_ctx: int = 2048,
) -> dict[str, Any]:
    """Call the selected agent provider and preserve native tool calls."""
    if _selected_agent_provider() == "openrouter":
        return _openrouter_chat_raw(
            messages,
            tools=tools,
            timeout=timeout,
            system_extra=system_extra,
            max_output_tokens=max_output_tokens,
            num_ctx=num_ctx,
        )

    selected_model = choose_ready_model(model or FAST_MODEL)
    effective_output, effective_ctx = _effective_limits(
        selected_model,
        max_output_tokens,
        num_ctx,
    )

    system = SYSTEM_PROMPT
    if system_extra.strip():
        system += "\n\n" + system_extra.strip()

    payload: dict[str, Any] = {
        "model": selected_model,
        "messages": _messages(messages, system),
        "stream": False,
        "think": False,
        "keep_alive": _keep_alive(selected_model),
        "options": _payload_options(
            selected_model,
            effective_output,
            effective_ctx,
            structured=False,
        ),
    }
    if tools:
        payload["tools"] = tools

    response = _SESSION.post(URL, json=payload, timeout=timeout)
    response.raise_for_status()
    body = response.json()

    try:
        from runtime.token_state import update as update_token_state
        update_token_state(
            model=selected_model,
            context_limit=effective_ctx,
            prompt_tokens=int(body.get("prompt_eval_count") or 0),
            output_tokens=int(body.get("eval_count") or 0),
        )
    except (ImportError, TypeError, ValueError):
        pass

    message = body.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("Ollama returned an invalid chat message.")
    return message
