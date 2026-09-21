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
    print("=" * 32)

    results = []

    results.append(check("Python", lambda: sys.version.split()[0]))
    results.append(check("PySide6", lambda: __import__("PySide6").__version__))
    results.append(check("PyAutoGUI", lambda: __import__("pyautogui").__version__))
    results.append(check("Vosk", lambda: __import__("vosk").__version__ if hasattr(__import__("vosk"), "__version__") else "installed"))

    def graph_file():
        path = Path("memory/graph.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        return f"{len(data.get('nodes', []))} memory nodes"

    results.append(check("Memory Galaxy seed", graph_file))

    def tools():
        from tools.registry import discover
        found = discover()
        return ", ".join(sorted(found)) or "none"

    results.append(check("Dynamic tools", tools))
    results.append(check("Brain package", lambda: __import__("brain").__name__))

    def ollama():
        import requests
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        response.raise_for_status()
        models = {item.get("name") for item in response.json().get("models", [])}
        return "Ollama reachable: " + ", ".join(sorted(models))

    results.append(check("Ollama", ollama))

    def fast_model():
        import requests
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        response.raise_for_status()
        names = {item.get("name") for item in response.json().get("models", [])}
        if "qwen2.5:3b" not in names:
            raise RuntimeError("qwen2.5:3b is not installed")
        return "qwen2.5:3b available"

    results.append(check("Fast model", fast_model))

    voice_path = Path("voice_models") / "vosk-model-small-en-us-0.15"
    results.append(check("Vosk model", lambda: "present" if voice_path.exists() else (_ for _ in ()).throw(FileNotFoundError(voice_path))))

    passed = sum(results)
    print("=" * 32)
    print(f"RESULT: {passed}/{len(results)} checks passed")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
