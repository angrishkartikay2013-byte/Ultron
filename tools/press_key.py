from __future__ import annotations

import pyautogui

TOOL = {
    "name": "press_key",
    "description": "Press one keyboard key such as enter, escape, tab, space, or F5.",
}

pyautogui.FAILSAFE = True


def run(key: str = "", **kwargs) -> str:
    key = key.strip().lower()
    if not key:
        raise ValueError("No key was supplied.")

    pyautogui.press(key)
    return f"Pressed {key}."
