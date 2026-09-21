# ULTRON

ULTRON GENESIS is a local Windows AI desktop assistant built around Ollama, Qwen3, Vosk, PySide6 and a growing tool system.

## Current Genesis features

- Floating bottom-right holographic orb
- Glass command popup positioned next to the orb
- Vosk microphone input with remembered device selection
- Local Qwen3 conversation through Ollama
- Persistent conversation memory in `memory/conversation.json`
- Windows speech output with interrupt support
- Press **Y** to interrupt listening, thinking or speech
- Double-click the orb to open the Memory Galaxy
- Seeded memory graph for Founder, ULTRON, School, Sanitary Business, Roblox and YouTube

## Run

From the repository root:

```powershell
uv run genesis.py
```

Keep the local Ollama model available as `qwen3:8b` and the Vosk model at:

```
voice_models/vosk-model-small-en-us-0.15
```

Runtime models and generated memory files are intentionally ignored by Git.

## Direction

GENESIS is being built as a desktop AI operating layer: persistent memory, a mission engine, dynamic tools, a richer 3D Memory Galaxy, and a protected Tool Workshop.
