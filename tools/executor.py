from __future__ import annotations

from typing import Any

from .registry import discover


def execute(mission: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry = discover()
    results: list[dict[str, Any]] = []

    for index, step in enumerate(mission, start=1):
        if not isinstance(step, dict):
            results.append({"step": index, "ok": False, "error": "Mission step is not an object."})
            continue

        tool_name = step.get("tool")
        arguments = step.get("arguments", {})

        if not isinstance(tool_name, str):
            results.append({"step": index, "ok": False, "error": "Missing tool name."})
            break

        if not isinstance(arguments, dict):
            results.append({"step": index, "ok": False, "error": "Tool arguments must be an object."})
            break

        spec = registry.get(tool_name)
        if spec is None:
            results.append({"step": index, "ok": False, "error": f"Unknown tool: {tool_name}"})
            break

        try:
            output = spec.run(**arguments)
            results.append(
                {"step": index, "tool": tool_name, "ok": True, "output": str(output)}
            )
        except Exception as exc:
            results.append(
                {"step": index, "tool": tool_name, "ok": False, "error": str(exc)}
            )
            break

    return results
