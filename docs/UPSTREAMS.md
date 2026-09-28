# ULTRON V2/V3 upstream projects

ULTRON is an integration project. External projects remain external; we do not vendor or blindly copy their source into this repository.

| Component | Upstream | Role |
| --- | --- | --- |
| Local model runtime / native tool calling | https://github.com/ollama/ollama | **Core** — local model runtime and native tool-calling backend. |
| Ollama Python client and examples | https://github.com/ollama/ollama-python | **Core candidate** — official Python client/reference implementation. |
| Streaming speech recognition | https://github.com/moonshine-ai/moonshine | **Core** — on-device low-latency voice stack. |
| Local speech synthesis | https://github.com/OHF-Voice/piper1-gpl | **Core** — current Piper development repository; the old rhasspy/piper repository is archived and points here. |
| Windows UI | https://github.com/pyside/pyside-setup | **Core** — official Qt for Python / PySide6 source repository. |
| Desktop automation | https://github.com/asweigart/pyautogui | **Core** — mouse, keyboard, screenshot and GUI automation. |
| Voice activity detection | https://github.com/snakers4/silero-vad | **Core candidate** — robust speech activity detection for hands-free listening. |
| Browser automation | https://github.com/browser-use/browser-use | **Integration** — browser agents, real-browser control, extraction and MCP/browser tooling. |
| Windows AgentOS / desktop automation | https://github.com/microsoft/UFO | **Integration/reference** — Windows UIA, Win32/WinCOM and hybrid GUI/API automation. |
| Multi-agent orchestration | https://github.com/microsoft/agent-framework | **Optional/reference** — current Microsoft framework for Python/.NET agent workflows and future C#/.NET components. |
| Native C/C++ LLM inference | https://github.com/ggml-org/llama.cpp | **Reference/future** — useful for the separate C++ ULTRON LLM engine and native inference experiments. |

## Separate ULTRON repository

The repository angrishkartikay2013-byte/llm is the custom C++ ULTRON LLM engine. It is intentionally maintained separately from this desktop assistant.

## Integration rule

Do not add an upstream project to the runtime dependency set merely because it appears in this document. Each integration must earn its place through a concrete ULTRON feature, compatibility test, and dependency review.

| MCP Python SDK | https://github.com/modelcontextprotocol/python-sdk | **P0 / integration** — standard tool/resource protocol; use this for external tool adapters. |

| MCP reference servers | https://github.com/modelcontextprotocol/servers | **P1 / reference** — filesystem, fetch, memory, git and sequential-thinking examples; reference only, not blindly production-vendored. |

| Windows UI automation | https://github.com/pywinauto/pywinauto | **P0 / integration** — Win32 and Microsoft UI Automation control-level access. |

| Browser automation | https://github.com/microsoft/playwright-python | **P0 / integration** — deterministic Chromium/Firefox/WebKit browser control. |

| Self-hosted web search | https://github.com/searxng/searxng | **P1 / integration** — HTTP search API for grounded web search. |
