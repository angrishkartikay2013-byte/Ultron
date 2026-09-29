from __future__ import annotations

import json

from ecosystem.runtime import describe, status_report, summary


TOOL = {
    "name": "ecosystem",
    "description": (
        "Inspect ULTRON's external AI ecosystem. "
        "Use action='status' to check installed components or "
        "action='describe' with a component id/path/repository to inspect one."
    ),
}


def run(action: str = "status", component: str = "") -> str:
    action = action.strip().lower()

    if action == "status":
        return json.dumps(
            {
                "summary": summary(),
                "components": status_report(component or None),
            },
            ensure_ascii=False,
            indent=2,
        )

    if action == "describe":
        if not component.strip():
            raise ValueError("component is required for action='describe'.")
        return json.dumps(
            describe(component),
            ensure_ascii=False,
            indent=2,
        )

    raise ValueError("action must be 'status' or 'describe'.")
