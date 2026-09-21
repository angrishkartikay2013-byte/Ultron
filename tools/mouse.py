import pyautogui

TOOL = {
    "name": "mouse_move",
    "description": "Move the mouse cursor."
}

pyautogui.FAILSAFE = True

def run(x, y):
    pyautogui.moveTo(int(x), int(y), duration=0.25)
    return f"Mouse moved to ({x},{y})"