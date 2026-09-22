from __future__ import annotations

import base64
import json
import os
import subprocess
import threading
import time
from typing import Any, Iterator

import requests

from .router import AGENT_MODEL, FAST_MODEL, HEAVY_MODEL, MID_MODEL, VISION_MODEL

BASE_URL = os.getenv("ULTRON_OLLAMA_URL", "http://127.0.0.1:11434")
URL = f"{BASE_URL}/api/chat"
OLLAMA_MODELS = os.getenv("OLLAMA_MODELS", r"E:\ULTRON\models")
OLLAMA_EXE = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
CPU_THREADS = max(4, os.cpu_count() or 4)

SYSTEM_PROMPT = """You are ULTRON GENESIS, a local Windows desktop assistant.
Address the user as Founder.
Be concise, direct, useful, and natural.
Speech input can contain obvious transcription or grammar errors; silently infer intent.
Do not mention corrections.
Do not reveal private chain-of-thought.
For normal conversation, answer in at most 2 short sentences unless the user asks for detail.
"""

_SESSION = requests.Session()
_OLLAMA_READY = False
_INSTALLED_MODELS: set[str] | None = None
_LOADED_MODELS: tuple[set[str], float] | None = None
_LOADED_LOCK = threading.Lock()


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
            if now - timestamp < 0.5:
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
    """Choose the best model that is already resident; never trigger a load."""
    loaded = resident_models(refresh=True)

    priorities = {
        HEAVY_MODEL: (HEAVY_MODEL, MID_MODEL, FAST_MODEL, AGENT_MODEL),
        MID_MODEL: (MID_MODEL, FAST_MODEL, AGENT_MODEL),
        FAST_MODEL: (FAST_MODEL, AGENT_MODEL),
        AGENT_MODEL: (AGENT_MODEL,),
        VISION_MODEL: (VISION_MODEL,),
    }

    for candidate in priorities.get(preferred, (preferred, FAST_MODEL, AGENT_MODEL)):
        if candidate in loaded:
            return candidate

    # The reflex brain should be the first warm brain. If even that is not
    # resident yet, let the normal selection logic choose an installed fallback.
    return AGENT_MODEL if AGENT_MODEL in loaded else choose_model(preferred)


def choose_model(preferred: str) -> str:
    models = installed_models()

    if preferred in models:
        return preferred

    if preferred == AGENT_MODEL:
        if FAST_MODEL in models:
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
        return {
            "temperature": 0.15,
            "top_p": 0.85,
            "top_k": 30,
            "num_ctx": num_ctx,
            "num_predict": max_output_tokens,
            "num_thread": CPU_THREADS,
            "num_batch": 128,
            "num_gpu": 0,
        }

    return {
        "temperature": 0.1,
        "top_p": 0.8,
        "top_k": 20,
        "num_ctx": num_ctx,
        "num_predict": max_output_tokens,
        "num_thread": CPU_THREADS,
        "num_batch": 128,
        "num_gpu": 0,
    }


def _keep_alive(model: str) -> str:
    if model in {AGENT_MODEL, FAST_MODEL}:
        return "90m"
    if model == MID_MODEL:
        return "15m"
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
    # Warm the tiny reflex brain first when installed, then the 1.5B fast brain.
    # If the tiny model is absent, warm_model() transparently falls back.
    reflex = warm_model(AGENT_MODEL)
    fast = warm_model(FAST_MODEL)
    return reflex, fast


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

    response = _SESSION.post(
        URL,
        json={
            "model": selected_model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": "5m",
            "options": _payload_options(selected_model, max_output_tokens, 768),
        },
        timeout=timeout,
    )
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
) -> str:
    selected_model = choose_ready_model(model or FAST_MODEL)
    system = SYSTEM_PROMPT
    if system_extra.strip():
        system += "\n\n" + system_extra.strip()

    response = _SESSION.post(
        URL,
        json={
            "model": selected_model,
            "messages": _messages(history, system),
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
    system = SYSTEM_PROMPT
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
                max_output_tokens,
                num_ctx,
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
