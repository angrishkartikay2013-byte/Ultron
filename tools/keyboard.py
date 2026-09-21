from __future__ import annotations

import pyautogui

TOOL = {
    "name": "type_text",
    "description": "Type text into the currently focused Windows application.",
}

pyautogui.FAILSAFE = True


def run(text: str = "", content: str = "", **kwargs) -> str:
    value = text or content
    if not value:
        raise ValueError("No text was supplied.")

    pyautogui.write(value, interval=0.01)
    return f"Typed {len(value)} characters."
