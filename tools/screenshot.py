from pathlib import Path
from datetime import datetime
import pyautogui

TOOL = {
    "name": "take_screenshot",
    "description": "Take a screenshot of the screen."
}

def run():
    folder = Path("screenshots")
    folder.mkdir(exist_ok=True)

    filename = datetime.now().strftime("screen_%Y%m%d_%H%M%S.png")
    path = folder / filename

    pyautogui.screenshot().save(path)

    return f"📸 Screenshot saved: {path}"