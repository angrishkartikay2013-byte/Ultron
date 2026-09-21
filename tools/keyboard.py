import pyautogui

TOOL = {
    "name": "type_text",
    "description": "Type text into the currently focused window."
}

pyautogui.FAILSAFE = True

def run(text):
    pyautogui.write(text, interval=0.02)
    return f"Typed {len(text)} characters."