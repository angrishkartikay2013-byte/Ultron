from __future__ import annotations

import time

TOOL = {
    "name": "wait",
    "description": "Wait for a number of seconds before the next mission step.",
}


def run(seconds: float = 1.0) -> str:
    seconds = max(0.0, min(float(seconds), 30.0))
    time.sleep(seconds)
    return f"Waited {seconds:g} seconds."
