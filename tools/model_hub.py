from __future__ import annotations

TOOL = {
    "name": "model_hub",
    "description": "Inspect Hugging Face Hub models or datasets. Does not download weights unless explicitly requested through the action.",
}

def run(action: str, query: str = "", limit: int = 10) -> str:
    """Discover Hugging Face assets using the official hub client."""
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise RuntimeError("huggingface_hub is not installed. Run scripts\\setup_ecosystem.ps1 -WithEnvironments.") from exc

    api = HfApi()
    limit = max(1, min(limit, 30))
    if action == "models":
        items = api.list_models(search=query or None, limit=limit)
        return "\n".join(f"- {x.id}" for x in items) or "No models found."
    if action == "datasets":
        items = api.list_datasets(search=query or None, limit=limit)
        return "\n".join(f"- {x.id}" for x in items) or "No datasets found."
    raise ValueError("action must be one of: models, datasets")
