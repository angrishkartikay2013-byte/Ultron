# ULTRON GENESIS

ULTRON is a local Windows AI desktop assistant built around Ollama, Qwen models, Vosk, PySide6 and a dynamic desktop tool system.

## Current system

- Floating holographic orb
- Glass command popup
- Fast reflex responses for basic conversation
- Fast local model routing with a Qwen2.5 3B first stage
- Qwen3 8B escalation for heavier reasoning and failed missions
- Persistent conversation memory
- Dynamic tool registry with exact argument signatures
- Desktop mission execution
- App launching, typing, mouse movement, clicking, hotkeys, key presses, scrolling and screenshots
- Interruptible offline SAPI5 speech
- Automatic microphone gain for quiet speech
- Optional Indian-English Vosk model support
- Interactive 3D-style Memory Galaxy with orbit, zoom and node selection

## Run

From the repository root:

```powershell
uv sync
uv run diagnostics.py
uv run genesis.py
```

### Better Indian-English recognition

The project can use Vosk's `vosk-model-small-en-in-0.4` when it exists under `voice_models/`. Install it with:

```powershell
uv run scripts/setup_indian_voice.py
```

The official Vosk model list describes that model as a lightweight Indian-English model, while the current US-English model is a lightweight generic English model. citeturn934909search0turn857853view0

### Model pipeline

GENESIS warms the fast model while the orb starts. Normal conversation and simple actions use the fast model; heavy tasks can switch to Qwen3 8B. The heavy model is not loaded for every simple interaction.

## Development direction

The next major layers are a richer mission HUD, persistent project vaults, true graph search/navigation, Tool Workshop approvals, Sentinel security monitoring, and deeper 3D presentation.
