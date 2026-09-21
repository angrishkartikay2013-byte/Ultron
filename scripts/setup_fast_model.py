from __future__ import annotations

import os
import subprocess

OLLAMA = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
MODEL_DIR = r"E:\ULTRON\models"
MODELS = [
    "qwen2.5:0.5b-instruct",
    "qwen2.5:1.5b",
]


def main() -> None:
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = MODEL_DIR

    for model in MODELS:
        print(f"Pulling {model} into {MODEL_DIR}...")
        subprocess.run([OLLAMA, "pull", model], env=env, check=True)
        print(f"{model} is ready.")

    print("\nULTRON speed stack is ready.")
    print("Agent: qwen2.5:0.5b-instruct")
    print("Fast:  qwen2.5:1.5b")


if __name__ == "__main__":
    main()
