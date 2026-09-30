from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BROWSER_PYTHON = ROOT / "external" / "envs" / "browser-use" / "Scripts" / "python.exe"
WORKER = ROOT / "scripts" / "browser_agent_worker.py"
BROWSER_CACHE = ROOT / "external" / "browser-cache"

TOOL = {
    "name": "browser_agent",
    "description": "Run a multi-step browser task with Browser Use in ULTRON's isolated E-drive environment and a local Ollama model.",
}


def run(task: str, model: str = "") -> str:
    """Execute a natural-language browser mission in the isolated Browser Use environment."""
    if not task.strip():
        raise ValueError("task must not be empty")
    if not BROWSER_PYTHON.exists():
        raise RuntimeError(
            "Browser Use environment is missing. Run "
            "scripts\\setup_ecosystem.ps1 -WithEnvironments."
        )
    if not WORKER.exists():
        raise RuntimeError(f"Browser worker script is missing: {WORKER}")

    selected = model.strip() or os.getenv("ULTRON_BROWSER_MODEL", "qwen3:8b")
    env = os.environ.copy()
    env["OLLAMA_HOST"] = os.getenv("ULTRON_OLLAMA_URL", "http://127.0.0.1:11434")
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSER_CACHE)

    completed = subprocess.run(
        [str(BROWSER_PYTHON), str(WORKER), task, selected],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or "Browser Use worker failed.")

    output = completed.stdout.strip()
    if not output:
        raise RuntimeError("Browser Use worker returned no result.")
    return output
