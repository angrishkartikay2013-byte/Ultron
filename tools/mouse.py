from __future__ import annotations

import pyautogui

TOOL = {
    "name": "mouse_move",
    "description": "Move the Windows mouse cursor by coordinates or a screen position such as top-right.",
}

pyautogui.FAILSAFE = True

POSITIONS = {
    "top-left": (0.05, 0.05),
    "top-right": (0.95, 0.05),
    "bottom-left": (0.05, 0.95),
    "bottom-right": (0.95, 0.95),
    "center": (0.50, 0.50),
    "middle": (0.50, 0.50),
}


def run(
    x: int | float | None = None,
    y: int | float | None = None,
    position: str = "",
    target: str = "",
    **kwargs,
) -> str:
    screen = pyautogui.size()

    selected = (position or target).strip().lower()
    if selected:
        if selected not in POSITIONS:
            raise ValueError(f"Unknown screen position '{selected}'.")
        px, py = POSITIONS[selected]
        x = int(screen.width * px)
        y = int(screen.height * py)

    if x is None and y is None:
        raise ValueError("Provide both x and y, or a position like 'top-right'.")
    if x is None:
        x = screen.width // 2
    if y is None:
        y = screen.height // 2

    x = max(0, min(int(x), screen.width - 1))
    y = max(0, min(int(y), screen.height - 1))

    pyautogui.moveTo(x, y, duration=0.18)
    return f"Mouse moved to ({x}, {y})."
