from __future__ import annotations

import ast
import re
from pathlib import Path


TOOL = {
    "name": "create_tool",
    "description": "Create a Python tool under tools/generated, validate its syntax, and optionally enable it.",
}

ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "tools" / "generated"


def _safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip())
    value = value.strip("_").lower()
    if not value or value[0].isdigit():
        raise ValueError("Tool name must start with a letter or underscore.")
    return value


def _validate(code: str) -> None:
    tree = ast.parse(code, filename="generated_tool.py")
    has_run = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "run"
        for node in tree.body
    )
    if not has_run:
        raise ValueError("Generated tool must define run(...).")


def run(
    name: str,
    code: str,
    description: str = "Generated ULTRON tool",
    enabled: bool = False,
) -> str:
    tool_name = _safe_name(name)
    if len(code) > 40_000:
        raise ValueError("Generated tool is too large.")

    _validate(code)

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    path = GENERATED_DIR / f"{tool_name}.py"

    wrapped = (
        "from __future__ import annotations\n\n"
        f"TOOL = {{'name': {tool_name!r}, 'description': {description!r}}}\n"
        f"ENABLED = {bool(enabled)!r}\n\n"
        f"{code.rstrip()}\n"
    )

    compile(wrapped, str(path), "exec")
    path.write_text(wrapped, encoding="utf-8")

    state = "enabled" if enabled else "staged"
    return f"Created {tool_name}.py ({state}) at {path}"
