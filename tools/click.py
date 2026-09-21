from __future__ import annotations

import pyautogui

TOOL = {
    "name": "mouse_click",
    "description": "Click the current mouse position or a supplied x/y coordinate.",
}

pyautogui.FAILSAFE = True


def run(
    x: int | None = None,
    y: int | None = None,
    button: str = "left",
    clicks: int = 1,
    **kwargs,
) -> str:
    if x is not None and y is not None:
        pyautogui.moveTo(int(x), int(y), duration=0.12)

    if button not in {"left", "right", "middle"}:
        raise ValueError("button must be left, right, or middle.")

    pyautogui.click(button=button, clicks=max(1, min(int(clicks), 3)))
    return f"Clicked {button} button."
