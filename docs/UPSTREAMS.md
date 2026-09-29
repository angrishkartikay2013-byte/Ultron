# ULTRON V2/V3 upstream projects

ULTRON is an integration project. External projects remain external; we do not vendor or blindly copy their source into this repository.

| Component | Upstream | Role |
| --- | --- | --- |
| Local model runtime / native tool calling | https://github.com/ollama/ollama | **Core** — local model runtime and native tool-calling backend. |
| Ollama Python client and examples | https://github.com/ollama/ollama-python | **Core candidate** — official Python client/reference implementation. |
| Streaming speech recognition | https://github.com/moonshine-ai/moonshine | **Core** — on-device low-latency voice stack. |
| Local speech synthesis | https://github.com/OHF-Voice/piper1-gpl | **Core** — local neural TTS. |
| Windows UI | https://github.com/pyside/pyside-setup | **Core** — official Qt for Python / PySide6. |
| Desktop automation | https://github.com/asweigart/pyautogui | **Core** — mouse, keyboard, screenshots and GUI automation. |
| Voice activity detection | https://github.com/snakers4/silero-vad | **Optional** — hands-free speech activity detection. |
| Browser automation | https://github.com/browser-use/browser-use | **Core integration** — browser agents and web workflows. |
| Deterministic browser control | https://github.com/microsoft/playwright-python | **Core integration** — browser automation and verification. |
| Windows AgentOS / desktop automation | https://github.com/microsoft/UFO | **Core integration** — Windows UIA, Win32/WinCOM and visual desktop control. |
| Windows UI fallback | https://github.com/pywinauto/pywinauto | **Core integration** — Win32 and Microsoft UI Automation fallback. |
| Agent-to-agent protocol | https://github.com/a2aproject/A2A | **Core integration** — independent AI agents communicate and collaborate through a common protocol. |
| A2A Python SDK | https://github.com/a2aproject/a2a-python | **Core integration** — Python implementation of the A2A protocol. |
| Stateful orchestration | https://github.com/langchain-ai/langgraph | **Core integration** — long-running, stateful mission graphs and checkpoints. |
| MCP Python SDK | https://github.com/modelcontextprotocol/python-sdk | **Core integration** — portable tool/resource protocol. |
| MCP reference servers | https://github.com/modelcontextprotocol/servers | **Reference** — filesystem, fetch, git, memory, sequential thinking and time examples. |
| Image generation | https://github.com/Comfy-Org/ComfyUI | **Core creative integration** — node-based generative media workflow backend. |
| Video generation | https://github.com/Wan-Video/Wan2.2 | **Core creative integration** — open video generation backend, normally offloaded from low-power desktop hardware. |
| Coding coworker | https://github.com/OpenHands/OpenHands | **Core integration** — larger software-engineering missions. |
| Model gateway | https://github.com/BerriAI/litellm | **Optional** — multi-provider model routing and cloud fallback. |
| Typed agent workers | https://github.com/pydantic/pydantic-ai | **Optional** — typed agent loop and worker experiments. |
| Graph-native agent memory | https://github.com/neo4j-labs/agent-memory | **Optional** — graph-oriented short/long/reasoning memory backend. |
| Persistent memory layer | https://github.com/mem0ai/mem0 | **Optional** — alternative semantic memory backend. |
| Self-hosted web search | https://github.com/searxng/searxng | **Optional** — research/search endpoint for grounded web retrieval. |
| Hugging Face Hub | https://github.com/huggingface/huggingface_hub | **Core integration** — model, dataset and artifact discovery/download adapter. |
| Realtime voice infrastructure | https://github.com/livekit/agents | **Optional/future** — networked WebRTC voice agents; not required for local desktop V2. |
| Native C/C++ LLM inference | https://github.com/ggml-org/llama.cpp | **Reference/future** — native inference reference for the separate C++ LLM project. |
| Microsoft Agent Framework | https://github.com/microsoft/agent-framework | **Optional/reference** — alternative Microsoft agent workflow stack for future .NET/C# workers. |

## Separate ULTRON repository

The repository `angrishkartikay2013-byte/llm` is the custom C++ ULTRON LLM engine. It remains separate from the desktop assistant.

## Integration policy

Do not add an upstream project to the core runtime merely because it appears in this document. Each integration must earn its place through a concrete ULTRON feature, compatibility test, and dependency review.

Use one primary orchestration layer, one primary coworker protocol, and one primary tool protocol. Optional frameworks are isolated and evaluated before becoming runtime dependencies.

See `ecosystem/components.json`, `ecosystem/agents.json` and `ecosystem/README.md` for the operational configuration and bootstrap layout.
