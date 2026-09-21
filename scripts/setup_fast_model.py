from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OLLAMA = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"))
MODEL_DIR = ROOT / "models"
MODELS = [
    "qwen2.5:0.5b-instruct",
    "qwen2.5:1.5b",
]
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
    print("Restarting Ollama with the E: model directory...")
    stop_ollama()
    start_ollama()

    env = os.environ.copy()
    env["OLLAMA_MODELS"] = str(MODEL_DIR)

    for model in MODELS:
        print(f"\nPulling {model} into {MODEL_DIR}...")
        subprocess.run([str(OLLAMA), "pull", model], env=env, check=True)
        print(f"{model} is ready.")

    print("\nULTRON speed stack is ready.")
    print("Agent: qwen2.5:0.5b-instruct")
    print("Fast:  qwen2.5:1.5b")
    print(f"Stored under: {MODEL_DIR}")


if __name__ == "__main__":
    main()
