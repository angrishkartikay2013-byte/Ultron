from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ecosystem" / "components.json"
EXTERNAL_ROOT = Path(r"E:\ULTRON\external")
REPOS_ROOT = EXTERNAL_ROOT / "repos"
ENVS_ROOT = EXTERNAL_ROOT / "envs"


@dataclass(frozen=True)
class Component:
    component_id: str
    repo: str
    path: str
    tier: str
    role: str
    runtime: str
    install: bool
    status: str
    environment: str | None = None

    @property
    def repo_path(self) -> Path:
        return REPOS_ROOT / self.path

    @property
    def env_path(self) -> Path | None:
        return ENVS_ROOT / self.environment if self.environment else None

    @property
    def installed(self) -> bool:
        if self.status in {"integrated-in-core", "separate-llm-repository"}:
            return True
        return self.repo_path.is_dir()


def _read_manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("ULTRON ecosystem manifest must be a JSON object.")
    return data


def components() -> list[Component]:
    raw = _read_manifest().get("components", [])
    if not isinstance(raw, list):
        raise RuntimeError("ULTRON ecosystem manifest has no components list.")
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        result.append(Component(
            component_id=str(item.get("id", "")),
            repo=str(item.get("repo", "")),
            path=str(item.get("path", "")),
            tier=str(item.get("tier", "")),
            role=str(item.get("role", "")),
            runtime=str(item.get("runtime", "")),
            install=bool(item.get("install", False)),
            status=str(item.get("status", "")),
            environment=str(item["environment"]) if item.get("environment") else None,
        ))
    return result


def get_component(component_id: str) -> Component:
    wanted = component_id.strip().lower()
    for item in components():
        if wanted in {item.component_id.lower(), item.repo.lower(), item.path.lower()}:
            return item
    raise KeyError(f"Unknown ecosystem component: {component_id}")


def status_report(component_id: str | None = None) -> list[dict[str, Any]]:
    selected = [get_component(component_id)] if component_id else components()
    return [{
        "id": item.component_id,
        "repo": item.repo,
        "role": item.role,
        "tier": item.tier,
        "runtime": item.runtime,
        "repo_path": str(item.repo_path),
        "repo_present": item.installed,
        "environment": str(item.env_path) if item.env_path else None,
        "environment_present": item.env_path.is_dir() if item.env_path else None,
        "manifest_status": item.status,
    } for item in selected]


def describe(component_id: str) -> dict[str, Any]:
    item = get_component(component_id)
    return {
        "id": item.component_id,
        "repo": item.repo,
        "path": str(item.repo_path),
        "tier": item.tier,
        "role": item.role,
        "runtime": item.runtime,
        "install": item.install,
        "manifest_status": item.status,
        "environment": str(item.env_path) if item.env_path else None,
        "repo_present": item.installed,
        "environment_present": item.env_path.is_dir() if item.env_path else None,
    }


def summary() -> dict[str, int]:
    items = components()
    return {
        "total": len(items),
        "present": sum(item.installed for item in items),
        "planned": sum(
            item.install and item.status not in {"integrated-in-core", "separate-llm-repository"}
            for item in items
        ),
        "optional": sum(item.tier == "optional" for item in items),
    }
