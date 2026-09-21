from __future__ import annotations

import pyautogui

TOOL = {
    "name": "hotkey",
    "description": "Press a keyboard shortcut such as ctrl+l or alt+tab.",
}

pyautogui.FAILSAFE = True


def run(keys: str = "", shortcut: str = "", **kwargs) -> str:
    value = (keys or shortcut).strip().lower()
    if not value:
        raise ValueError("No keyboard shortcut was supplied.")

    parts = [part.strip() for part in value.replace("-", "+").split("+") if part.strip()]
    if not parts:
        raise ValueError("Invalid keyboard shortcut.")

    pyautogui.hotkey(*parts)
    return f"Pressed {value}."
