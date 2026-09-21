from __future__ import annotations

import io
import json
import re
from typing import Any

import pyautogui
from PIL import Image

from brain.llm import vision_chat


TOOL = {
    "name": "screen_vision",
    "description": (
        "Use ULTRON's visual cortex to inspect the current Windows screen. "
        "Actions: describe, locate, click, double_click. For locate/click, "
        "pass a plain-language target such as 'the blue Download button'."
    ),
}

pyautogui.FAILSAFE = True


def _capture() -> bytes:
    image = pyautogui.screenshot()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"Vision model did not return coordinates: {text}")
    value = json.loads(text[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("Vision model returned an invalid object.")
    return value


def _locate(task: str, action: str) -> dict[str, Any]:
    width, height = pyautogui.size()
    prompt = (
        f"Screen size is {width}x{height} pixels. "
        f"Find this target on the screenshot: {task!r}. "
        "Return ONLY JSON in this exact shape: "
        '{"found":true,"x":123,"y":456,"label":"target","confidence":0.92}. '
        'If it is not visible, return {"found":false,"x":0,"y":0,'
        '"label":"","confidence":0}. '
        "Use screen pixel coordinates, not normalized coordinates."
    )
    raw = vision_chat(prompt, _capture(), max_output_tokens=96)
    data = _extract_json(raw)

    found = bool(data.get("found"))
    x = int(data.get("x", 0))
    y = int(data.get("y", 0))
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))

    result = {
        "found": found,
        "x": x,
        "y": y,
        "label": str(data.get("label", "")),
        "confidence": float(data.get("confidence", 0)),
    }

    if not found:
        return result

    if action == "click":
        pyautogui.click(x, y)
        result["action"] = f"clicked ({x}, {y})"
    elif action == "double_click":
        pyautogui.doubleClick(x, y, interval=0.08)
        result["action"] = f"double-clicked ({x}, {y})"
    else:
        result["action"] = f"located ({x}, {y})"

    return result


def run(task: str = "", action: str = "describe", **kwargs) -> str:
    task = task.strip()
    action = action.strip().lower()

    if action not in {"describe", "locate", "click", "double_click"}:
        raise ValueError(
            "action must be one of: describe, locate, click, double_click"
        )

    if not task and action != "describe":
        raise ValueError("A visual target is required.")

    if action == "describe":
        prompt = (
            "Describe the current Windows screen briefly. Mention the active "
            "application, major visible windows, important buttons/controls, "
            "and readable text that would help another agent operate it."
        )
        return vision_chat(prompt, _capture(), max_output_tokens=180)

    result = _locate(task, action)
    return json.dumps(result, ensure_ascii=False)


def screenshot_bytes_for_vision() -> bytes:
    return _capture()
