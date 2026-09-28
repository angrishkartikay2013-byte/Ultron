# ULTRON V2 upstream projects

ULTRON is an integration project; upstream dependencies remain external and are not vendored into this repository.

| Component | Upstream |
| --- | --- |
| Local model runtime / native tool calling | https://github.com/ollama/ollama |
| Ollama Python client and examples | https://github.com/ollama/ollama-python |
| Streaming speech recognition | https://github.com/moonshine-ai/moonshine |
| Local speech synthesis | https://github.com/rhasspy/piper |
| Windows UI | https://github.com/qtproject/pyside-pyside-setup |
| Desktop automation | https://github.com/asweigart/pyautogui |

The separate angrishkartikay2013-byte/llm repository remains the custom C++ LLM engine. It is intentionally not vendored here.

| Local speech synthesis | https://github.com/OHF-Voice/piper1-gpl | **Core** — current Piper development repository; the former rhasspy/piper repo is archived and points here. |

| Voice activity detection | https://github.com/snakers4/silero-vad | **Core candidate** — robust VAD for hands-free listening; current upstream has v6.2.x releases. |

| Browser automation | https://github.com/browser-use/browser-use | **Integration** — web tasks, browser control, extraction, and MCP/browser tooling. |

| Windows AgentOS / desktop automation | https://github.com/microsoft/UFO | **Integration/reference** — Windows UI Automation, Win32/WinCOM, hybrid GUI/API execution, and multi-application workflows. |

| Multi-agent orchestration | https://github.com/microsoft/agent-framework | **Optional/reference** — current Microsoft framework for Python/.NET multi-agent workflows; useful for future C#/.NET shell or specialized agent orchestration. |
