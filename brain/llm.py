from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any, Iterator

import requests

from .router import AGENT_MODEL, FAST_MODEL, HEAVY_MODEL, MID_MODEL

BASE_URL = os.getenv("ULTRON_OLLAMA_URL", "http://127.0.0.1:11434")
URL = f"{BASE_URL}/api/chat"
OLLAMA_MODELS = os.getenv("OLLAMA_MODELS", r"E:\ULTRON\models")
OLLAMA_EXE = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
CPU_THREADS = max(4, os.cpu_count() or 4)

SYSTEM_PROMPT = """You are ULTRON GENESIS, a local Windows desktop assistant.
Address the user as Founder.
Be concise, direct, useful, and natural.
User input may come from speech recognition and can contain small spelling, grammar, punctuation, or transcription errors.
Silently infer the intended wording and intent. Do not mention the correction.
Do not reveal private chain-of-thought.
Prefer short answers unless the user asks for detail.
"""


_SESSION = requests.Session()


def ensure_ollama() -> None:
    try:
        _SESSION.get(f"{BASE_URL}/api/tags", timeout=1.2)
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
            _SESSION.get(f"{BASE_URL}/api/tags", timeout=0.8)
            return
        except requests.RequestException:
            time.sleep(0.3)

    raise RuntimeError("Ollama did not become available on 127.0.0.1:11434")


def installed_models() -> set[str]:
    ensure_ollama()
    response = _SESSION.get(f"{BASE_URL}/api/tags", timeout=5)
    response.raise_for_status()
    return {
        item.get("name", "")
        for item in response.json().get("models", [])
        if item.get("name")
    }


def choose_model(preferred: str) -> str:
    models = installed_models()

    if preferred in models:
        return preferred

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
) -> dict[str, Any]:
    if model == HEAVY_MODEL:
        threads = CPU_THREADS
        batch = 128
        temperature = 0.15
    else:
        threads = CPU_THREADS
        batch = 96
        temperature = 0.1

    return {
        "temperature": temperature,
        "top_p": 0.85,
        "top_k": 30,
        "num_ctx": num_ctx,
        "num_predict": max_output_tokens,
        "num_thread": threads,
        "num_batch": batch,
        "num_gpu": 0,
    }


def _keep_alive(model: str) -> str:
    if model in {AGENT_MODEL, FAST_MODEL}:
        return "90m"
    if model == MID_MODEL:
        return "20m"
    return "10m"


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
            "options": _payload_options(selected, 1, 512),
        },
        timeout=120,
    )
    response.raise_for_status()
    return selected


def warm_speed_stack() -> tuple[str, str]:
    # Operator and conversation agents share the same fast model.
    fast = warm_model(FAST_MODEL)
    return fast, fast


def chat(
    history: list[dict[str, str]],
    timeout: int = 90,
    system_extra: str = "",
    model: str | None = None,
    max_output_tokens: int = 96,
    num_ctx: int = 1024,
) -> str:
    selected_model = choose_model(model or FAST_MODEL)
    ensure_ollama()

    system = SYSTEM_PROMPT
    if system_extra.strip():
        system += "\n\n" + system_extra.strip()

    response = _SESSION.post(
        URL,
        json={
            "model": selected_model,
            "messages": [
                {"role": "system", "content": system},
                *history,
            ],
            "stream": False,
            "think": False,
            "keep_alive": _keep_alive(selected_model),
            "options": _payload_options(
                selected_model,
                max_output_tokens,
                num_ctx,
            ),
        },
        timeout=timeout,
    )
    response.raise_for_status()

    data: dict[str, Any] = response.json()
    content = data.get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError("Ollama returned an invalid response.")
    return content.strip()


def stream_chat(
    history: list[dict[str, str]],
    timeout: int = 90,
    system_extra: str = "",
    model: str | None = None,
    max_output_tokens: int = 96,
    num_ctx: int = 1024,
) -> Iterator[str]:
    selected_model = choose_model(model or FAST_MODEL)
    ensure_ollama()

    system = SYSTEM_PROMPT
    if system_extra.strip():
        system += "\n\n" + system_extra.strip()

    response = _SESSION.post(
        URL,
        json={
            "model": selected_model,
            "messages": [
                {"role": "system", "content": system},
                *history,
            ],
            "stream": True,
            "think": False,
            "keep_alive": _keep_alive(selected_model),
            "options": _payload_options(
                selected_model,
                max_output_tokens,
                num_ctx,
            ),
        },
        timeout=(2.5, timeout),
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
