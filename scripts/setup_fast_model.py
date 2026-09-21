from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OLLAMA = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"))
MODEL_DIR = ROOT / "models"
MODEL = "qwen2.5:0.5b-instruct"
VISION_MODEL = "qwen2.5vl:3b"
BASE_URL = "http://127.0.0.1:11434"


def stop_ollama() -> None:
    for image in ("Ollama App.exe", "ollama.exe"):
        subprocess.run(
            ["taskkill", "/IM", image, "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def start_ollama() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["OLLAMA_MODELS"] = str(MODEL_DIR)
    env["OLLAMA_HOST"] = "127.0.0.1:11434"
    env["OLLAMA_KEEP_ALIVE"] = "90m"
    env["OLLAMA_MAX_LOADED_MODELS"] = "2"
    env["OLLAMA_NUM_PARALLEL"] = "1"

    subprocess.Popen(
        [str(OLLAMA), "serve"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    for _ in range(40):
        try:
            requests.get(f"{BASE_URL}/api/tags", timeout=1)
            return
        except requests.RequestException:
            time.sleep(0.25)

    raise RuntimeError("Ollama did not start on 127.0.0.1:11434")


def main() -> None:
    if not OLLAMA.exists():
        raise FileNotFoundError(f"Ollama executable not found: {OLLAMA}")

    print(f"ULTRON model directory: {MODEL_DIR}")
    print(f"Installing reflex model: {MODEL}")
    print(f"Installing visual cortex: {VISION_MODEL}")
    stop_ollama()
    start_ollama()

    env = os.environ.copy()
    env["OLLAMA_MODELS"] = str(MODEL_DIR)

    subprocess.run([str(OLLAMA), "pull", MODEL], env=env, check=True)
    subprocess.run([str(OLLAMA), "pull", VISION_MODEL], env=env, check=True)

    print(f"\n{MODEL} and {VISION_MODEL} are ready.")
    print(f"Stored under: {MODEL_DIR}")
    print("Existing 1.5B / 3B / 8B models are left untouched.")


if __name__ == "__main__":
    main()
