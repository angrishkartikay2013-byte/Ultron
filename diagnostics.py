from __future__ import annotations

import importlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def check(label: str, fn) -> bool:
    try:
        value = fn()
        print(f"[OK] {label}: {value}")
        return True
    except Exception as exc:
        print(f"[FAIL] {label}: {type(exc).__name__}: {exc}")
        return False


def _voice_status() -> str:
    voice = importlib.import_module("voice")
    return (
        f"Moonshine={getattr(voice, '_MOONSHINE_MODEL_NAME', 'configured')}, "
        f"Piper={Path('voice_models/piper/en_US-ryan-high.onnx').exists()}"
    )


def _memory_nodes() -> int:
    data = json.loads(
        (ROOT / "memory" / "graph.json").read_text(encoding="utf-8")
    )
    return len(data.get("nodes", []))


def _ecosystem_status() -> str:
    runtime = importlib.import_module("ecosystem.runtime")
    status = runtime.summary()
    return (
        f"{status['present']}/{status['total']} present, "
        f"{status['planned']} planned, {status['optional']} optional"
    )


def main() -> int:
    print("ULTRON GENESIS DIAGNOSTICS")
    print("=" * 46)

    checks = [
        ("Python", lambda: __import__("sys").version.split()[0]),
        ("PySide6", lambda: importlib.import_module("PySide6").__version__),
        ("PyAutoGUI", lambda: importlib.import_module("pyautogui").__version__),
        (
            "Moonshine Voice",
            lambda: importlib.import_module("moonshine_voice").__name__,
        ),
        ("Piper TTS", lambda: importlib.import_module("piper").__name__),
        ("Voice stack", _voice_status),
        ("Memory Galaxy", _memory_nodes),
        (
            "Dynamic tools",
            lambda: ", ".join(
                sorted(importlib.import_module("tools.registry").discover())
            ),
        ),
        ("Brain router", lambda: importlib.import_module("brain.router").FAST_MODEL),
        (
            "Ollama models",
            lambda: ", ".join(
                sorted(
                    __import__(
                        "brain.llm",
                        fromlist=["installed_models"],
                    ).installed_models()
                )
            ),
        ),
        (
            "Speed stack",
            lambda: (
                f"{importlib.import_module('brain.router').AGENT_MODEL} -> "
                f"{importlib.import_module('brain.router').FAST_MODEL} -> "
                f"{importlib.import_module('brain.router').MID_MODEL} -> "
                f"{importlib.import_module('brain.router').HEAVY_MODEL}"
            ),
        ),
        (
            "Ecosystem manifest",
            lambda: str((ROOT / "ecosystem" / "components.json").exists()),
        ),
        ("Ecosystem status", _ecosystem_status),
    ]

    passed = sum(check(label, fn) for label, fn in checks)

    print("=" * 46)
    print(f"RESULT: {passed}/{len(checks)} checks passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
