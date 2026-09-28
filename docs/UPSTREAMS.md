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
