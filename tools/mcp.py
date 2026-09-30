from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

TOOL = {
    "name": "mcp",
    "description": "Discover and call configured Model Context Protocol servers. Server commands are read from the local MCP config.",
}

CONFIG = Path(os.getenv("ULTRON_MCP_CONFIG", "config/mcp_servers.json"))

async def _call(server: dict, tool_name: str, arguments: dict) -> str:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as exc:
        raise RuntimeError("MCP Python SDK is not installed. Run scripts\\setup_ecosystem.ps1 -WithEnvironments.") from exc

    params = StdioServerParameters(
        command=server["command"],
        args=server.get("args", []),
        env=server.get("env"),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if tool_name == "__list__":
                result = await session.list_tools()
                return json.dumps(
                    [{"name": t.name, "description": t.description} for t in result.tools],
                    ensure_ascii=False,
                )
            result = await session.call_tool(tool_name, arguments)
            return json.dumps(result.model_dump() if hasattr(result, "model_dump") else str(result), ensure_ascii=False)

def run(server: str, action: str, tool_name: str = "", arguments_json: str = "{}") -> str:
    """List or call a tool on a named configured MCP server."""
    if not CONFIG.exists():
        raise RuntimeError(f"MCP config not found: {CONFIG}")
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    servers = data.get("servers", {})
    if server not in servers:
        raise ValueError(f"Unknown MCP server {server!r}. Available: {', '.join(servers) or 'none'}")
    if action == "list":
        tool_name = "__list__"
    elif action != "call" or not tool_name:
        raise ValueError("action must be list or call; call requires tool_name")
    arguments = json.loads(arguments_json)
    return asyncio.run(_call(servers[server], tool_name, arguments))
