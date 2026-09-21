
import json
import time
import pkgutil
import importlib
from pathlib import Path

import requests

# ==========================================================
# CONFIG
# ==========================================================

VERSION = "v0.6 Alpha - Mission Engine"
MODEL = "qwen3:8b"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

BASE_DIR = Path(__file__).parent
TOOLS_DIR = BASE_DIR / "tools"
MEMORY_FILE = BASE_DIR / "memory" / "memory.json"

# ==========================================================
# MEMORY
# ==========================================================

if not MEMORY_FILE.exists():
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps({
        "user": {"name": "Kartikay"},
        "memories": [],
        "projects": {
            "ultron": {
                "version": VERSION,
                "status": "online"
            }
        }
    }, indent=2))

memory = json.loads(MEMORY_FILE.read_text())
USERNAME = memory.get("user", {}).get("name", "Kartikay")

# ==========================================================
# LOAD TOOLS AUTOMATICALLY
# ==========================================================

TOOLS = {}

for module in pkgutil.iter_modules([str(TOOLS_DIR)]):
    mod = importlib.import_module(f"tools.{module.name}")

    if hasattr(mod, "TOOL") and hasattr(mod, "run"):
        TOOLS[mod.TOOL["name"]] = mod

tool_list = "\n".join(
    f"- {tool.TOOL['name']}: {tool.TOOL['description']}"
    for tool in TOOLS.values()
)

# ==========================================================
# ULTRON SYSTEM PROMPT
# ==========================================================

SYSTEM_PROMPT = f"""
You are ULTRON, Kartikay's AI operating system.

Available tools:
{tool_list}

When the user asks you to do something on the PC,
reply ONLY with JSON.

Single action example:

{{
  "tool":"open_app",
  "arguments":{{"app":"paint"}}
}}

Mission example:

{{
  "mission":[
    {{"tool":"open_app","arguments":{{"app":"notepad"}}}},
    {{"tool":"wait","arguments":{{"seconds":1}}}},
    {{"tool":"type_text","arguments":{{"text":"Hello Founder"}}}}
  ]
}}

Rules:
- Use "mission" for multiple steps.
- Use "wait" when a program needs time to open.
- If no tool is needed, reply with plain text.
- Never include reasoning.
- Never include markdown.
"""

# ==========================================================
# TALK TO OLLAMA
# ==========================================================


def ask_ultron(prompt: str):

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "think": False
        },
        timeout=300
    )

    response.raise_for_status()

    return response.json()["response"]


# ==========================================================
# EXECUTE ONE TOOL
# ==========================================================


def execute_single(tool_name, arguments):

    if tool_name == "wait":
        seconds = float(arguments.get("seconds", 1))
        time.sleep(seconds)
        return f"⏳ Waited {seconds} second(s)."

    tool = TOOLS.get(tool_name)

    if tool is None:
        return f"❌ Unknown tool: {tool_name}"

    try:
        return tool.run(**arguments)

    except Exception as e:
        return f"❌ {tool_name}: {e}"


# ==========================================================
# EXECUTE AI RESPONSE
# ==========================================================


def execute_response(reply):

    try:
        data = json.loads(reply)

    except json.JSONDecodeError:
        return None

    outputs = []

    if "mission" in data:

        print("🚀 Starting mission...")

        for i, step in enumerate(data["mission"], start=1):

            tool_name = step.get("tool")
            arguments = step.get("arguments", {})

            print(f"Step {i}: {tool_name}")

            result = execute_single(tool_name, arguments)

            outputs.append(result)

        print("✅ Mission complete.")

        return "\n".join(outputs)

    if "tool" in data:
        return execute_single(
            data["tool"],
            data.get("arguments", {})
        )

    return None


# ==========================================================
# MEMORY
# ==========================================================


def save_memory(text):

    memory.setdefault("memories", []).append(text)

    MEMORY_FILE.write_text(json.dumps(memory, indent=2))


def show_memory():

    print("\n====== MEMORY ======\n")

    memories = memory.get("memories", [])

    if not memories:
        print("No memories saved.")
    else:
        for i, item in enumerate(memories, start=1):
            print(f"{i}. {item}")

    print("\n====================")


# ==========================================================
# BOOT SCREEN
# ==========================================================

print("=" * 60)
print("           U L T R O N   G E N E S I S")
print("=" * 60)
print(f"🧠 Brain    : {MODEL}")
print(f"👤 User     : {USERNAME}")
print(f"🔧 Tools    : {len(TOOLS)} loaded")
print(f"🚀 Version  : {VERSION}")
print("=" * 60)

for tool in TOOLS.values():
    print("✓", tool.TOOL["name"])

print("=" * 60)
print("Type 'help' for commands.")
print("Type 'exit' to shut down.")
print("=" * 60)

# ==========================================================
# LOOP
# ==========================================================

while True:

    command = input("\nULTRON > ").strip()

    if command == "":
        continue

    lower = command.lower()

    if lower == "exit":
        print("👋 ULTRON shutting down...")
        break

    if lower == "help":

        print("""
remember <text>
memory
exit

Everything else is handled by ULTRON AI.
""")
        continue

    if lower.startswith("remember "):
        save_memory(command[9:])
        print("💾 Memory saved.")
        continue

    if lower == "memory":
        show_memory()
        continue

    print("\n🧠 ULTRON...\n")

    try:
        reply = ask_ultron(command)

        result = execute_response(reply)

        if result is None:
            print(reply)
        else:
            print(result)

    except requests.exceptions.ConnectionError:
        print("❌ ULTRON brain is offline.")
        print("Run: ollama serve")

    except Exception as e:
        print("❌ Error")
        print(e)