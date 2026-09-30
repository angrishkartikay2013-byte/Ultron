# ULTRON V2 status

## Source-tree status

**V2 architecture: COMPLETE**

The repository now contains the intended core V2 architecture:

- Voice-first Windows assistant flow
- Qwen3 8B agency brain by default
- Native Ollama function/tool calling
- Live tool schemas generated from real function signatures
- Multi-round tool execution with grounded results
- Durable memory store and model-accessible memory tool
- Existing screen vision integration
- Dynamic Tool Workshop staging with syntax validation
- Ctrl+Y interruption and headless voice runtime
- Runtime/model/recording ignore rules
- GitHub sanity workflow

## Local validation status

**Pending on the founder machine.**

The GitHub repository cannot execute ULTRON against the founder's microphone, Windows desktop, installed Ollama models, or local audio devices. After pulling main, the founder should run the normal diagnostics and launcher and exercise voice, tool use, vision, memory, interruption, and shutdown.

## V2 completion gate

V2 is considered operationally complete when the local machine confirms:

1. ULTRON starts without a thread/lifecycle error.
2. Moonshine loads from the E: drive cache.
3. Qwen3 8B can answer normal conversation naturally.
4. Native tool calls successfully launch/type/click on Windows.
5. Screen vision can inspect and act on a visible target.
6. Memory can be stored and recalled across sessions.
7. Ctrl+Y interrupts speech/active work.
8. Tool Workshop stages generated tools without auto-enabling them.
