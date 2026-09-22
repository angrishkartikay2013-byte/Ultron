from __future__ import annotations

import inspect
from typing import Any

from .registry import discover


def execute(mission: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry = discover()
    results: list[dict[str, Any]] = []

    for index, step in enumerate(mission, start=1):
        if not isinstance(step, dict):
            return [{"step": index, "ok": False, "error": "Mission step is not an object."}]

        tool_name = step.get("tool")
        arguments = step.get("arguments", {})

        if not isinstance(tool_name, str):
            return [{"step": index, "ok": False, "error": "Missing tool name."}]
        if not isinstance(arguments, dict):
            return [{"step": index, "ok": False, "error": "Tool arguments must be an object."}]

        spec = registry.get(tool_name)
        if spec is None:
            return [{
                "step": index,
                "ok": False,
                "error": f"Unknown tool '{tool_name}'. Available: {', '.join(sorted(registry))}",
            }]

        try:
            signature = inspect.signature(spec.run)
            signature.bind(**arguments)
            output = spec.run(**arguments)
            results.append({
                "step": index,
                "tool": tool_name,
                "ok": True,
                "output": str(output),
            })
        except TypeError as exc:
            results.append({
                "step": index,
                "tool": tool_name,
                "ok": False,
                "error": f"Bad arguments: {exc}. Expected {spec.name}{spec.signature}",
            })
            break
        except Exception as exc:
            results.append({
                "step": index,
                "tool": tool_name,
                "ok": False,
                "error": str(exc),
            })
            break

    return results
