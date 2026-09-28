# ULTRON GENESIS

ULTRON GENESIS is a local, voice-first Windows AI assistant designed as an agent system rather than a chatbot wrapped in a UI.

## V2 architecture

**Voice → Agency Brain → Native Tools → Real Execution Results → Agency Brain → Voice**

The V2 agency loop uses Ollama's native function/tool-calling API. Ollama documents tool calling through the `tools` field and tool result messages; its current Python examples also support multiple tool calls in a loop. See the official Ollama tool-calling documentation and examples at https://ollama.com/blog/tool-support and https://github.com/ollama/ollama-python/blob/main/examples/tools.py.

### Brain regions

- **Agency Cortex:** Qwen3 8B by default. Interprets requests, chooses tools, sequences missions and decides when the task is complete.
- **Conversation Cortex:** Qwen2.5 3B remains available for lightweight voice/UI work.
- **Vision Cortex:** Qwen2.5VL 3B reads the current screen through the existing `screen_vision` tool.
- **Voice Cortex:** Moonshine Voice handles live microphone transcription; Piper handles spoken output.
- **Memory Cortex:** conversation history plus durable memory tools and the Memory Galaxy UI.
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
- Memory Galaxy visualization
- Tool Workshop for syntax-checked generated tools
- Ctrl+Y interruption
- Floating orb HUD with heard/interpreting/conclusion states
- Local-first model and voice assets

## Run

From the repository root:

`uv sync`

`uv run diagnostics.py`

`uv run genesis.py`

## Model setup

Set `ULTRON_AGENT_MODEL` to test another compatible Ollama model. Llama 3.1 is also supported by Ollama's documented tool-calling interface. See https://ollama.com/blog/tool-support.

## Repository strategy

The assistant remains in this repository. The separate `llm` repository is reserved for the custom C++ LLM engine.

## V2 completion criteria

ULTRON V2 is considered feature-complete in the source tree when the following are present and integrated:

1. Native tool calling
2. Dynamic tool registry
3. Real tool execution feedback
4. Voice/STT/TTS lifecycle
5. Screen vision tool
6. Durable memory and Memory Galaxy
7. Tool Workshop
8. Interruptible orb UI
9. Clean runtime ignore rules
10. Local setup and diagnostics documentation

Local hardware validation is still required on the target Windows machine after pulling the release commit.
