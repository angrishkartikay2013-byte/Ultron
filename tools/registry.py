from __future__ import annotations

import importlib
import importlib.util
import inspect
import pkgutil
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, get_args, get_origin, get_type_hints


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    run: Callable[..., Any]
    signature: str


def _type_schema(annotation: Any) -> dict[str, Any]:
    if annotation is inspect._empty:
        return {"type": "string"}

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in {list, tuple, set}:
        item_type = args[0] if args else str
        return {"type": "array", "items": _type_schema(item_type)}

    if origin in {dict}:
        return {"type": "object"}

    if origin in {types.UnionType} or str(origin).endswith("typing.Union"):
        non_none = [item for item in args if item is not type(None)]
        if not non_none:
            return {"type": "string"}
        if len(non_none) == 1:
            schema = _type_schema(non_none[0])
            return {"anyOf": [schema, {"type": "null"}]}
        return {"anyOf": [_type_schema(item) for item in non_none] + [{"type": "null"}]}

    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}

    return {"type": "string"}


def _tool_parameters(spec: ToolSpec) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    try:
        hints = get_type_hints(spec.run)
    except Exception:
        hints = {}

    for name, parameter in inspect.signature(spec.run).parameters.items():
        if name in {"self", "cls"}:
            continue
        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue

        annotation = hints.get(name, parameter.annotation)
        properties[name] = _type_schema(annotation)

        if parameter.default is inspect._empty:
            required.append(name)

    result: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        result["required"] = required
    return result


def ollama_tools() -> list[dict[str, Any]]:
    """Return the live registry as Ollama-native function tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": _tool_parameters(spec),
            },
        }
        for spec in sorted(discover().values(), key=lambda item: item.name)
    ]


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
