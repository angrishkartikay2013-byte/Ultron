from __future__ import annotations

import os
import subprocess
import time
from typing import Any

import requests

MODEL = os.getenv("ULTRON_MODEL", "qwen3:8b")
BASE_URL = os.getenv("ULTRON_OLLAMA_URL", "http://127.0.0.1:11434")
URL = f"{BASE_URL}/api/chat"

SYSTEM_PROMPT = """You are ULTRON GENESIS, a local desktop AI assistant.
Address the user as Founder.
Be concise, capable, calm, and practical.
Never expose private chain-of-thought.
Remember that the user is building ULTRON as a long-term second brain.
"""


def ensure_ollama() -> None:
    try:
        requests.get(f"{BASE_URL}/api/tags", timeout=1.5)
        return
    except requests.RequestException:
        pass

    env = os.environ.copy()
    env["OLLAMA_MODELS"] = env.get("OLLAMA_MODELS", r"E:\ULTRON\models")
    ollama = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")

    subprocess.Popen(
        [ollama, "serve"],
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


def chat(
    history: list[dict[str, str]],
    timeout: int = 180,
    system_extra: str = "",
) -> str:
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
            "model": MODEL,
            "messages": messages,
            "stream": False,
            "think": False,
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
