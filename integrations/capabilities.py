from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPTIONAL = {
    "mcp": "mcp",
    "playwright": "playwright",
    "pywinauto": "pywinauto",
    "huggingface_hub": "huggingface_hub",
    "browser_use": "browser_use",
    "silero_vad": "silero_vad",
}


def available() -> dict[str, bool]:
    result = {
        name: importlib.util.find_spec(module) is not None
        for name, module in OPTIONAL.items()
    }

    browser_env = ROOT / "external" / "envs" / "browser-use" / "Scripts" / "python.exe"
    if browser_env.exists():
        result["browser_use"] = True

    return result
