# ULTRON

ULTRON is a local, voice-first Windows AI assistant designed as an agent system rather than a chatbot wrapped in a UI.

## V2 architecture

**Voice → Agency Brain → Native Tools → Real Execution Results → Agency Brain → Voice**

The agency loop supports local Ollama tool calling and an OpenRouter-compatible hosted API path. With `OPENROUTER_API_KEY` present, `ULTRON_PROVIDER=auto` selects OpenRouter for the agent/tool loop; without a key, ULTRON uses Ollama locally. The hosted path converts ULTRON's tool messages to the OpenAI-compatible tool-call format, while desktop tools continue to execute on the Windows machine.

### Brain regions

- **Agency Cortex:** Qwen3 8B by default. Interprets requests, chooses tools, sequences missions and decides when the task is complete.
- **Conversation Cortex:** Qwen2.5 3B remains available for lightweight voice/UI work.
- **Vision Cortex:** Qwen2.5VL 3B reads the current screen through the existing `screen_vision` tool.
- **Voice Cortex:** Moonshine Voice handles live microphone transcription; Piper handles spoken output.
- **Memory Cortex:** conversation history plus durable memory tools.
- **Tool Workshop:** the dynamic registry can discover normal tools and staged generated tools.

## V2 feature set

- Voice-first continuous interaction
- Natural language without hard-coded command phrases
- Native Ollama tool calling
- Dynamic tool discovery from real Python signatures
- Multi-step tool execution with grounded feedback
- Windows app launching, typing, mouse, hotkeys, scrolling and screenshots
- Visual screen inspection and coordinate-based visual interaction
- Durable memory storage and recall
- Tool Workshop for syntax-checked generated tools
- Ctrl+Y interruption
- Minimal token-left HUD
- Local-first model and voice assets

## Interface

Run `uv run ultron.py`. The main window uses a dark instrument-panel HUD with a teal circular core and orange indicators. Click the core to open the neural conversation view. Text requests use the existing agency/tool-execution backend; the existing voice runtime stays available. The target Windows machine still needs a local launch test.

## Run

From the repository root:

`uv sync --extra runtime`

`uv run diagnostics.py`

`uv run ultron.py`

## Hosted API setup (OpenRouter)

ULTRON can use OpenRouter's free-model router for the agency brain while keeping Ollama available as the local fallback. The default model is `openrouter/free`; model availability and free-tier limits are controlled by the provider and can change.

In PowerShell, set the key for this terminal session without echoing it into the command history:

```powershell
$secureKey = Read-Host "Paste your OpenRouter API key" -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $env:OPENROUTER_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
}
$env:ULTRON_PROVIDER = "openrouter"
$env:ULTRON_OPENROUTER_MODEL = "openrouter/free"
uv run diagnostics.py
uv run ultron.py
```

To force local Ollama instead:

```powershell
$env:ULTRON_PROVIDER = "ollama"
uv run ultron.py
```

The default `ULTRON_PROVIDER=auto` uses OpenRouter when `OPENROUTER_API_KEY` is set and Ollama otherwise. The API key is read only from the environment; never commit it to the repository or paste it into chat. When using a hosted model, prompts and tool outputs sent to the agency model leave the PC and are processed by the selected provider. Don't send passwords, private documents, or other sensitive data to a hosted model.

## Model setup

Set `ULTRON_AGENT_MODEL` to test another compatible Ollama model. Llama 3.1 is also supported by Ollama's documented tool-calling interface. See https://ollama.com/blog/tool-support.

## Repository strategy

The ULTRON desktop assistant remains in this repository. The separate `llm` repository is reserved for the custom C++ LLM engine.

## V2 completion criteria

ULTRON V2 is considered feature-complete in the source tree when the following are present and integrated:

1. Native tool calling
2. Dynamic tool registry
3. Real tool execution feedback
4. Voice/STT/TTS lifecycle
5. Screen vision tool
6. Durable memory
7. Tool Workshop
8. Ctrl+Y interruption
9. Minimal token-left HUD
10. Local setup and diagnostics documentation

Local hardware validation is still required on the target Windows machine after pulling the release commit.


## ULTRON ecosystem

ULTRON now has an explicit external ecosystem registry in `ecosystem/components.json` and a coworker registry in `ecosystem/agents.json`.

The ecosystem is designed as a set of isolated capabilities around the existing ULTRON core:

- **Windows hands:** Microsoft UFO
- **Browser worker:** Browser Use (isolated) + Playwright (ULTRON runtime)
- **AI-to-AI coworkers:** A2A + the A2A Python SDK
- **Mission orchestration:** LangGraph
- **Tool protocol:** MCP Python SDK + reference servers
- **Image generation:** ComfyUI
- **Video generation:** Wan2.2
- **Coding coworker:** OpenHands
- **Optional model gateway:** LiteLLM
- **Optional graph/semantic memory:** Neo4j Agent Memory + Mem0
- **Optional self-hosted search:** SearXNG
- **Model/artifact discovery:** Hugging Face Hub
- **Windows fallback automation:** pywinauto
- **Optional voice activity detection:** Silero VAD

Large frameworks and model weights are intentionally kept outside the ULTRON source tree. Bootstrap targets `E:\\ULTRON\\external\\repos`, isolated environments live under `E:\\ULTRON\\external\\envs`, and caches are redirected to E:.

### Ecosystem setup

Run the core ecosystem bootstrap:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_ecosystem.ps1
```

To install the runtime integration packages into ULTRON's own `.venv`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_ecosystem.ps1 -WithEnvironments
```

For the full configured repository set plus all runtime adapters:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_ecosystem.ps1 -Everything -WithEnvironments
```

The bootstrap does **not** download ComfyUI or Wan model weights automatically. SearXNG source checkout is skipped on Windows because its current official deployment path is container-oriented.

Run diagnostics after setup:

```powershell
uv run diagnostics.py
uv run ultron.py
```

The separate `angrishkartikay2013-byte/llm` repository remains the custom C++ LLM engine; ULTRON is the desktop agent that can eventually use it as another local model backend.


## Runtime-integrated ecosystem

The bootstrap installs lightweight runtime adapters into ULTRON's own `.venv`. Browser Use is intentionally isolated because its current package pins `requests==2.33.0`, which conflicts with ULTRON's core Requests dependency. Browser Use is launched through its E-drive environment.

Run:

```powershell
uv sync --extra runtime
powershell -ExecutionPolicy Bypass -File .\scripts\setup_ecosystem.ps1 -Everything -WithEnvironments
uv run diagnostics.py
uv run ultron.py
```

Browser Use has native Ollama support, so the isolated browser worker can use ULTRON's local model stack without a cloud API key. The Browser Use project currently documents Python 3.11+ and local Ollama support.

SearXNG is intentionally not cloned by the Windows bootstrap. Its current official deployment documentation recommends container-based installation; ULTRON therefore treats it as an external optional service on Windows. The `browser_agent` remains the local browser-research path.
