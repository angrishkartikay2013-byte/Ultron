from __future__ import annotations

import importlib
import importlib.util
import inspect
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    run: Callable[..., Any]
    signature: str


def _add_module(found: dict[str, ToolSpec], module: Any) -> None:
    metadata = getattr(module, "TOOL", None)
    runner = getattr(module, "run", None)

    if not isinstance(metadata, dict) or not callable(runner):
        return

    name = metadata.get("name")
    description = metadata.get("description", "")

    if isinstance(name, str) and name.strip():
        found[name.strip()] = ToolSpec(
            name=name.strip(),
            description=str(description),
            run=runner,
            signature=str(inspect.signature(runner)),
        )


def _load_generated(found: dict[str, ToolSpec]) -> None:
    generated_dir = Path(__file__).resolve().parent / "generated"
    if not generated_dir.exists():
        return

    for path in sorted(generated_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue

        try:
            source = path.read_text(encoding="utf-8")
            if "ENABLED = True" not in source:
                continue

            module_name = f"tools.generated_{path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _add_module(found, module)
        except Exception:
            continue


def discover() -> dict[str, ToolSpec]:
    import tools

    found: dict[str, ToolSpec] = {}

    for module_info in pkgutil.iter_modules(tools.__path__):
        if module_info.name.startswith("_") or module_info.name == "generated":
            continue

        module = importlib.import_module(f"tools.{module_info.name}")
        _add_module(found, module)

    _load_generated(found)
    return found


def prompt_catalog() -> str:
    tools = discover()
    if not tools:
        return "No tools are currently available."

    lines = [
        f"- {spec.name}{spec.signature}: {spec.description}"
        for spec in sorted(tools.values(), key=lambda item: item.name)
    ]
    return "\n".join(lines)
