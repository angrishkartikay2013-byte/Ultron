from __future__ import annotations

import importlib.util

OPTIONAL = {
    "mcp": "mcp",
    "playwright": "playwright",
    "pywinauto": "pywinauto",
    "huggingface_hub": "huggingface_hub",
    "browser_use": "browser_use",
    "silero_vad": "silero_vad",
}

def available() -> dict[str, bool]:
    return {name: importlib.util.find_spec(module) is not None for name, module in OPTIONAL.items()}
