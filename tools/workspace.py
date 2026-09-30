from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TOOL = {
    "name": "workspace",
    "description": "Read, write, list, and create directories inside the ULTRON workspace. Paths are sandboxed to the project root.",
}

def _safe(path: str) -> Path:
    candidate = (ROOT / path).resolve()
    if candidate != ROOT and ROOT not in candidate.parents:
        raise ValueError("Path must stay inside the ULTRON workspace.")
    return candidate

def run(action: str, path: str = "", content: str = "") -> str:
    """Perform a safe workspace filesystem operation."""
    target = _safe(path) if path else ROOT
    if action == "list":
        items = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        return "\n".join(f"{'[DIR]' if p.is_dir() else '[FILE]'} {p.relative_to(ROOT)}" for p in items[:200])
    if action == "read":
        return target.read_text(encoding="utf-8")
    if action == "write":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {target.relative_to(ROOT)}."
    if action == "mkdir":
        target.mkdir(parents=True, exist_ok=True)
        return f"Created {target.relative_to(ROOT)}."
    raise ValueError("action must be one of: list, read, write, mkdir")
