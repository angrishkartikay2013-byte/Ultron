from __future__ import annotations

import os
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: browser_agent_worker.py <task> <model>", file=sys.stderr)
        return 2

    task = sys.argv[1].strip()
    model = sys.argv[2].strip()
    if not task:
        print("task must not be empty", file=sys.stderr)
        return 2

    from browser_use import Agent, ChatOllama

    os.environ.setdefault("OLLAMA_HOST", "http://127.0.0.1:11434")

    llm = ChatOllama(
        model=model or "qwen3:8b",
        num_ctx=int(os.getenv("ULTRON_BROWSER_NUM_CTX", "4096")),
    )
    result = Agent(task=task, llm=llm).run_sync()

    if hasattr(result, "final_result"):
        result = result.final_result()

    print(str(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
