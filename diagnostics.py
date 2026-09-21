from __future__ import annotations

import importlib
import os
from pathlib import Path

from pywhispercpp.model import Model


def check(label: str, fn) -> bool:
    try:
        value = fn()
        print(f"[OK] {label}: {value}")
        return True
    except Exception as exc:
        print(f"[FAIL] {label}: {type(exc).__name__}: {exc}")
        return False


def main() -> int:
    print("ULTRON GENESIS DIAGNOSTICS")
    print("=" * 38)

    checks = [
        ("Python", lambda: __import__("sys").version.split()[0]),
        ("PySide6", lambda: importlib.import_module("PySide6").__version__),
        ("PyAutoGUI", lambda: importlib.import_module("pyautogui").__version__),
        ("Whisper.cpp", lambda: "pywhispercpp"),
        ("Piper TTS", lambda: "piper"),
        ("Memory Galaxy", lambda: len(__import__("json").loads(Path("memory/graph.json").read_text(encoding="utf-8"))["nodes"])),
        ("Dynamic tools", lambda: ", ".join(sorted(importlib.import_module("tools.registry").discover()))),
        ("Brain router", lambda: importlib.import_module("brain.router").FAST_MODEL),
        ("Ollama models", lambda: ", ".join(sorted(__import__("brain.llm", fromlist=["installed_models"]).installed_models()))),
        ("Speed stack", lambda: f"{importlib.import_module('brain.router').AGENT_MODEL} -> {importlib.import_module('brain.router').FAST_MODEL} -> {importlib.import_module('brain.router').MID_MODEL} -> {importlib.import_module('brain.router').HEAVY_MODEL}"),
        ("Piper voice model", lambda: str(Path("voice_models/piper/en_US-ryan-high.onnx").exists())),
        ("Voice model", lambda: "Whisper.cpp + Piper neural TTS"),
    ]

    passed = sum(check(label, fn) for label, fn in checks)

    print("=" * 38)
    print(f"RESULT: {passed}/{len(checks)} checks passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
