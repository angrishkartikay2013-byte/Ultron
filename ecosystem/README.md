# ULTRON GENESIS Ecosystem

ULTRON GENESIS is the master desktop-agent project. Upstream projects remain external dependencies or isolated reference implementations; their source is not copied into the ULTRON core.

## Architecture

```
                           ULTRON GENESIS
                    Agency Brain + Voice + Orb
                                  |
             +--------------------+--------------------+
             |                    |                    |
          HANDS                BROWSER              MEMORY
        Microsoft UFO       Browser Use + Playwright  Local graph
             |                    |                 + optional backends
             |                    |
             +----------+---------+
                        |
                   TOOL FABRIC
               MCP + native tools
                        |
              +---------+----------+
              |                    |
           COWORKERS             CREATIVE
          A2A + workers       ComfyUI + Wan2.2
              |
        LangGraph stateful
          orchestration
              |
        optional model gateway
             LiteLLM
```

## What is already in the core

- Ollama native tool calling
- Qwen agency/conversation/vision model routing
- Moonshine streaming speech recognition
- Piper local neural speech
- PySide6 floating orb and Memory Galaxy
- PyAutoGUI desktop control
- Visual screen inspection
- Durable conversation and long-term memory
- Dynamic Python tool registry
- Tool execution feedback
- Tool Workshop / staged generated tools
- Microsoft UFO integration for Windows hands

## External integration layers

| Layer | Project | Purpose | Isolation |
| --- | --- | --- | --- |
| Hands | `microsoft/UFO` | Deep Windows UI automation | Existing UFO venv |
| Browser | `browser-use/browser-use` | Natural-language browser agent | `E:\\Titan\\envs\\browser-use` |
| Browser control | `microsoft/playwright-python` | Deterministic browser automation and verification | Browser env |
| Coworkers | `a2aproject/A2A` + `a2a-python` | Agent-to-agent communication | Agent stack |
| Orchestration | `langchain-ai/langgraph` | Stateful long-running missions | Agent stack |
| Tools | `modelcontextprotocol/python-sdk` | MCP adapters | Agent stack |
| Reference tools | `modelcontextprotocol/servers` | Filesystem, fetch, git, memory, time and reasoning references | Reference |
| Images | `Comfy-Org/ComfyUI` | Graph-based generation backend | Dedicated future env |
| Video | `Wan-Video/Wan2.2` | Open video generation backend | Dedicated future env / cloud |
| Coding coworker | `OpenHands/OpenHands` | Larger software-engineering missions | Dedicated env |
| Model gateway | `BerriAI/litellm` | Optional multi-provider routing and fallback | Dedicated env |
| Memory | `neo4j-labs/agent-memory` | Optional graph-native memory | Optional service |
| Memory | `mem0ai/mem0` | Optional persistent memory backend | Optional env/service |
| Search | `searxng/searxng` | Optional self-hosted research/search endpoint | Container/service |
| Model hub | `huggingface/huggingface_hub` | Model, dataset and artifact discovery | Agent stack |
| Windows fallback | `pywinauto/pywinauto` | Control-level Win32/UIA automation | Agent stack |
| Voice VAD | `snakers4/silero-vad` | Optional hands-free speech activity detection | Agent stack |
| Typed workers | `pydantic/pydantic-ai` | Optional typed worker/agent experiments | Agent stack |

## Hardware rule

The target PC has a 4-core Intel CPU, 16 GB RAM and Intel integrated graphics. Therefore:

- Do not download giant model weights during bootstrap.
- Do not put ComfyUI or Wan weights into the ULTRON repository.
- Prefer the existing local Qwen/Ollama stack for normal missions.
- Use creative models through a dedicated machine or cloud GPU when the workload exceeds the desktop hardware.
- Keep browser caches, Python caches and generated artifacts on E:.

## Directory layout

```
E:\\Titan\\
├── envs\\
│   ├── agent-stack\\
│   ├── browser-use\\
│   ├── comfyui\\
│   ├── model-gateway\\
│   └── openhands\\
├── repos\\
│   ├── UFO\\
│   ├── browser-use\\
│   ├── playwright-python\\
│   ├── A2A\\
│   ├── a2a-python\\
│   ├── LangGraph\\
│   ├── mcp-python-sdk\\
│   ├── mcp-servers\\
│   ├── ComfyUI\\
│   ├── Wan2.2\\
│   ├── OpenHands\\
│   └── ...
├── hf_cache\\
├── models\\
└── tmp\\
```

## Bootstrap

From the ULTRON repository root on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\setup_ecosystem.ps1
```

For optional components as well:

```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\setup_ecosystem.ps1 -Everything
```

For lightweight Python environments:

```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\setup_ecosystem.ps1 -WithEnvironments
```

The script never downloads ComfyUI/Wan model weights automatically.

## Runtime discovery

The file `ecosystem/components.json` is the source of truth. `ecosystem/runtime.py` reads it and `tools/ecosystem.py` exposes status to the existing ULTRON dynamic tool registry.

This means the agency brain can ask the live registry what ecosystem components are installed instead of relying on hard-coded command phrases.

## Integration policy

ULTRON should use the smallest number of overlapping frameworks necessary:

- LangGraph is the primary stateful orchestrator.
- A2A is the interoperability protocol for independent coworkers.
- MCP is the portable tool/resource interface.
- Browser Use + Playwright cover browser work.
- UFO remains the Windows hands layer.
- ComfyUI is the creative execution backend.
- Wan2.2 is a video backend, normally offloaded from the target PC.
- OpenHands is a specialist software-engineering coworker.
- LiteLLM, Mem0 and Neo4j memory remain optional until a concrete need justifies them.

Do not install multiple competing agent frameworks into the same environment merely because they exist.
