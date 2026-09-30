# ULTRON ecosystem master map

This file is the source of truth for ULTRON's external ecosystem. Status describes the current repository/runtime design, not whether every optional component is installed on the founder's machine.

## 1. What ULTRON already has

| Project / dependency | Function | Status |
| --- | --- | --- |
| Ollama | Local LLM runtime, model loading, chat API, native tool calling | **HAVE / CORE** |
| Qwen3 8B | Agency/reasoning model configured by default | **HAVE / CORE** |
| Qwen2.5 3B | Fast conversational model | **HAVE / CORE** |
| Qwen2.5VL 3B | Visual cortex model | **HAVE / CORE** |
| Moonshine Voice | Local streaming speech recognition | **HAVE / CORE** |
| Piper | Local text-to-speech | **HAVE / CORE** |
| PySide6 | Minimal token-left HUD | **HAVE / CORE** |
| PyAutoGUI | Mouse, keyboard and screenshot automation | **HAVE / CORE** |
| Requests | HTTP client for local/API integrations | **HAVE / CORE** |
| NumPy / Pillow | Audio/image/runtime support | **HAVE / CORE** |
| Custom memory store | Durable facts/preferences/project memory | **HAVE / CORE** |
| Dynamic tool registry | Discovers real Python tool signatures | **HAVE / CORE** |
| Tool Workshop | Syntax-checks and stages generated tools | **HAVE / CORE** |
| GitHub connector | Development/repository integration for the founder workflow | **HAVE / DEV TOOL** |
| Windows native shell/APIs | Processes, files, Shell/Win32 capabilities available through Python/Windows | **HAVE / PLATFORM** |

## 2. Repositories we should add/integrate next

| Repository | Purpose | Status | Priority |
| --- | --- | --- | --- |
| https://github.com/modelcontextprotocol/python-sdk | Standard MCP clients/servers and interoperable external tools | **RUNTIME ADAPTER** | **P0** |
| https://github.com/pywinauto/pywinauto | Windows UI Automation + Win32 control-level automation | **RUNTIME ADAPTER** | **P0** |
| https://github.com/microsoft/playwright-python | Reliable Chromium/Firefox/WebKit browser control | **RUNTIME ADAPTER** | **P0** |
| https://github.com/browser-use/browser-use | Higher-level browser agent and web-task automation | **RUNTIME ADAPTER** | **P1** |
| https://github.com/snakers4/silero-vad | Additional voice activity detection/fallback | **OPTIONAL RUNTIME ADAPTER** | **P1** |
| https://github.com/searxng/searxng | Self-hosted web metasearch with HTTP API | **OPTIONAL CONTAINER SERVICE** | **P1** |
| https://github.com/huggingface/huggingface_hub | Model/dataset discovery and asset management | **RUNTIME ADAPTER** | **P1** |
| https://github.com/microsoft/UFO | Advanced Windows AgentOS and GUI+API automation reference | **REFERENCE ONLY** | **P1** |
| https://github.com/modelcontextprotocol/servers | Reference MCP servers for filesystem, fetch, memory, git and more | **REFERENCE ONLY** | **P1** |
| https://github.com/microsoft/agent-framework | Future Python/.NET multi-agent orchestration | **REFERENCE / FUTURE** | **P2** |
| https://github.com/pydantic/pydantic-ai | Typed alternative agent framework | **OPTIONAL / EVALUATE** | **P2** |
| https://github.com/livekit/agents | Realtime networked voice-agent infrastructure | **OPTIONAL / FUTURE** | **P3** |
| https://github.com/ggml-org/llama.cpp | Native C/C++ inference path for the separate LLM project | **REFERENCE / FUTURE** | **P2** |
| https://github.com/google-gemini/cookbook | Gemini API examples, including Live API/search/tool patterns | **REFERENCE / OPTIONAL CLOUD** | **P3** |

## 3. APIs ULTRON already has

| API / interface | Used for | Status |
| --- | --- | --- |
| Ollama REST API | /api/chat, /api/tags, /api/ps, native tool calling | **HAVE** |
| Moonshine Python API | microphone transcription/events | **HAVE** |
| Piper Python API | local speech synthesis | **HAVE** |
| PyAutoGUI API | mouse/keyboard/screenshots | **HAVE** |
| PySide6/Qt API | minimal token HUD | **HAVE** |
| Local filesystem API | memory, tools, configs, screenshots | **HAVE** |
| Windows process/Shell APIs through Python | app launching and local desktop control | **HAVE** |
| GitHub API/connector | source-control development workflow | **HAVE FOR FOUNDER WORKFLOW** |

## 4. APIs / interfaces ULTRON should gain

| API / interface | Purpose | Status |
| --- | --- | --- |
| MCP stdio / Streamable HTTP / SSE | Plug external tools/resources into ULTRON through a standard protocol | **NEEDED / P0** |
| Windows UI Automation / Win32 / COM via pywinauto or equivalent | Precise control of real application controls instead of coordinate-only actions | **NEEDED / P0** |
| Playwright browser API | Deterministic browser control and extraction | **NEEDED / P0** |
| Browser Use API | Higher-level web-agent workflows | **NEEDED / P1** |
| SearXNG HTTP search API | Local/self-hosted web search for grounded browsing | **NEEDED / P1** |
| Hugging Face Hub API | Discover/download/manage model assets | **USEFUL / P1** |
| GitHub REST API inside ULTRON | Optional self-managed repo/issues/CI operations | **OPTIONAL / P2** |
| OpenAI API | Cloud fallback only | **NOT REQUIRED** |
| Gemini API / Live API | Cloud multimodal/voice/search fallback only | **NOT REQUIRED** |
| LiveKit/WebRTC APIs | Remote/mobile/network voice | **NOT REQUIRED FOR LOCAL V2** |

## 5. Important architecture rule

Do not install every repository in this table into the runtime.

ULTRON should keep a small local core and add capabilities through adapters. The intended direction is:

Voice
→ Agency Cortex
→ MCP/tool registry
→ native Windows APIs / UI Automation / browser
→ execution result
→ Agency Cortex
→ response
→ voice

MCP is the interoperability layer, not a replacement for ULTRON's own tool system.

## 6. Hardware-aware rule

The founder machine is CPU-only with 16 GB RAM. Heavy frameworks and large models must remain on-demand. The V2 design should prefer local, lightweight components and avoid running multiple large agent frameworks simultaneously.

## 7. Security rule

External tool servers are treated as untrusted extensions. Generated tools stay staged until approved. Any filesystem, shell, browser, Git, or network capability must have explicit scope/validation before production use.

## 8. Separate C++ project

https://github.com/angrishkartikay2013-byte/llm remains separate. llama.cpp is a reference/inference option for that project, not something ULTRON should vendor into this repository.
