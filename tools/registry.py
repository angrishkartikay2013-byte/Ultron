from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    run: Callable[..., Any]


def discover() -> dict[str, ToolSpec]:
    import tools

    found: dict[str, ToolSpec] = {}

    for module_info in pkgutil.iter_modules(tools.__path__):
        if module_info.name.startswith("_"):
            continue

        module = importlib.import_module(f"tools.{module_info.name}")
        metadata = getattr(module, "TOOL", None)
        runner = getattr(module, "run", None)

        if not isinstance(metadata, dict) or not callable(runner):
            continue

        name = metadata.get("name")
        description = metadata.get("description", "")

        if isinstance(name, str) and name.strip():
            found[name] = ToolSpec(
                name=name.strip(),
                description=str(description),
                run=runner,
            )

    return found


def prompt_catalog() -> str:
    tools = discover()
    if not tools:
        return "No tools are currently available."

    return "\n".join(
        f"- {spec.name}: {spec.description}"
        for spec in sorted(tools.values(), key=lambda item: item.name)
    )
