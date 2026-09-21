from __future__ import annotations

import pyautogui

TOOL = {
    "name": "scroll",
    "description": "Scroll the active Windows application vertically.",
}

pyautogui.FAILSAFE = True


def run(amount: int | float = 0, **kwargs) -> str:
    value = int(amount)
    if value == 0:
        raise ValueError("amount must be non-zero.")
    value = max(-20, min(20, value))
    pyautogui.scroll(value)
    return f"Scrolled {value}."
