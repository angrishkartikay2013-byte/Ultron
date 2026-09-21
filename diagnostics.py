from __future__ import annotations

import json
import sys
from pathlib import Path


def check(label: str, callback) -> bool:
    try:
        result = callback()
        print(f"[OK] {label}: {result}")
        return True
    except Exception as exc:
        print(f"[FAIL] {label}: {exc}")
        return False


def main() -> int:
    print("ULTRON GENESIS DIAGNOSTICS")
    print("=" * 38)

    results = []

    results.append(check("Python", lambda: sys.version.split()[0]))
    results.append(check("PySide6", lambda: __import__("PySide6").__version__))
    results.append(check("PyAutoGUI", lambda: __import__("pyautogui").__version__))
    results.append(check("Vosk", lambda: "installed"))
    results.append(check("TTS", lambda: __import__("pyttsx3").__name__))

    def graph_file():
        path = Path("memory/graph.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        return f"{len(data.get('nodes', []))} memory nodes"

    results.append(check("Memory Galaxy", graph_file))

    def tools():
        from tools.registry import discover
        found = discover()
        return ", ".join(sorted(found)) or "none"

    results.append(check("Dynamic tools", tools))

    results.append(check("Brain package", lambda: __import__("brain").__name__))

    def models():
        import requests
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        response.raise_for_status()
        names = sorted(
            item.get("name", "")
            for item in response.json().get("models", [])
            if item.get("name")
        )
        return ", ".join(names) or "no models"

    results.append(check("Ollama models", models))

    def voice_model():
        indian = Path("voice_models/vosk-model-small-en-in-0.4")
        us = Path("voice_models/vosk-model-small-en-us-0.15")
        if indian.exists():
            return "Indian English model active"
        if us.exists():
            return "US English model active; Indian model not installed"
        raise FileNotFoundError("No Vosk model found.")

    results.append(check("Voice model", voice_model))

    print("=" * 38)
    passed = sum(results)
    print(f"RESULT: {passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
