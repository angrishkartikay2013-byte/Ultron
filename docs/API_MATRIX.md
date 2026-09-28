# ULTRON API matrix

## Local APIs already in use

### Ollama
Base URL: `http://127.0.0.1:11434`

Current ULTRON uses:
- `GET /api/tags` — installed model discovery
- `GET /api/ps` — resident model discovery
- `POST /api/chat` — conversation, reasoning, vision and native tool calls

Keep model assets on the E: drive through the existing Ollama configuration.

### Voice
- Moonshine Voice Python API for microphone capture, VAD/segmentation and live transcript events.
- Piper Python API for local synthesis.

### Desktop
- PyAutoGUI for direct input/screenshot actions.
- Future UIA/Win32/COM adapter for control-aware application automation.

## APIs we should add

### MCP
Use the official Python SDK as the interoperability layer for external tools/resources. MCP v2 currently supports stdio, Streamable HTTP and SSE transports. https://github.com/modelcontextprotocol/python-sdk

### Browser
Use Playwright for deterministic browser primitives; put Browser Use above it when a task requires higher-level agent behavior.

### Search
Prefer a local/self-hosted SearXNG instance for web-search capability. It exposes HTTP search endpoints and can return JSON when configured for it. https://github.com/searxng/searxng

### Model assets
Use Hugging Face Hub for discovery/download/metadata when a model cannot be obtained through Ollama. https://github.com/huggingface/huggingface_hub

## Cloud APIs

Cloud providers remain optional adapters, not V2 requirements:
- OpenAI
- Gemini
- other compatible model providers

ULTRON V2 should work without API keys when using its local stack.

## API design rule

Every external API is wrapped behind a ULTRON adapter/tool. The agency brain should see capabilities, not vendor-specific implementation details.
