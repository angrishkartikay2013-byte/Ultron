from __future__ import annotations

import os
import subprocess
import time
from typing import Any

import requests

FAST_MODEL = os.getenv("ULTRON_FAST_MODEL", "qwen2.5:1.5b")
HEAVY_MODEL = os.getenv("ULTRON_HEAVY_MODEL", "qwen3:8b")
BASE_URL = os.getenv("ULTRON_OLLAMA_URL", "http://127.0.0.1:11434")
URL = f"{BASE_URL}/api/chat"
OLLAMA_MODELS = os.getenv("OLLAMA_MODELS", r"E:\ULTRON\models")
OLLAMA_EXE = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")

SYSTEM_PROMPT = """You are ULTRON GENESIS, a local desktop AI assistant.
Address the user as Founder.
Be concise, capable, calm, and practical.
Never expose private chain-of-thought.
Use one or two short sentences for normal conversation.
"""


def ensure_ollama() -> None:
    try:
        requests.get(f"{BASE_URL}/api/tags", timeout=1.5)
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
            requests.get(f"{BASE_URL}/api/tags", timeout=1.0)
            return
        except requests.RequestException:
            time.sleep(0.5)

    raise RuntimeError("Ollama did not become available on 127.0.0.1:11434")


def installed_models() -> set[str]:
    ensure_ollama()
    response = requests.get(f"{BASE_URL}/api/tags", timeout=5)
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

    if preferred == FAST_MODEL and HEAVY_MODEL in models:
        return HEAVY_MODEL

    if HEAVY_MODEL in models:
        return HEAVY_MODEL

    if models:
        return sorted(models)[0]

    raise RuntimeError("No Ollama models are installed.")


def warm_model(model: str = FAST_MODEL) -> str:
    selected = choose_model(model)
    payload = {
        "model": selected,
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {"num_predict": 1},
    }
    response = requests.post(f"{URL}", json=payload, timeout=120)
    response.raise_for_status()
    return selected


def chat(
    history: list[dict[str, str]],
    timeout: int = 120,
    system_extra: str = "",
    model: str | None = None,
    max_output_tokens: int = 128,
) -> str:
    selected_model = choose_model(model or FAST_MODEL)
    ensure_ollama()

    system = SYSTEM_PROMPT
    if system_extra.strip():
        system += "\n\n" + system_extra.strip()

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        *history,
    ]

    response = requests.post(
        URL,
        json={
            "model": selected_model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {
                "num_predict": max_output_tokens,
                "temperature": 0.2,
                "num_ctx": 2048,
            },
        },
        timeout=timeout,
    )

    response.raise_for_status()

    data: dict[str, Any] = response.json()
    message = data.get("message", {})
    content = message.get("content")

    if not isinstance(content, str):
        raise RuntimeError("Ollama returned an invalid response.")

    return content.strip()
