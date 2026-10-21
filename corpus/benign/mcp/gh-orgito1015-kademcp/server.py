"""
CTF Solver MCP Server
Exposes tools for Reversing/Pwn, Crypto, Web, and Forensics challenges.
"""

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from tools.crypto import crypto_tools, handle_crypto
from tools.forensics import forensics_tools, handle_forensics
from tools.reversing import handle_reversing, reversing_tools
from tools.web import handle_web, web_tools

server = Server("ctf-solver")

ALL_TOOLS = reversing_tools + crypto_tools + web_tools + forensics_tools

TOOL_HANDLERS = {}
for tool in reversing_tools:
    TOOL_HANDLERS[tool.name] = handle_reversing
for tool in crypto_tools:
    TOOL_HANDLERS[tool.name] = handle_crypto
for tool in web_tools:
    TOOL_HANDLERS[tool.name] = handle_web
for tool in forensics_tools:
    TOOL_HANDLERS[tool.name] = handle_forensics


@server.list_tools()
async def list_tools() -> list[Tool]:
    return ALL_TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    try:
        result = await handler(name, arguments)
    except Exception as e:
        return [TextContent(type="text", text=f"[error] tool '{name}' failed: {e}")]
    return [TextContent(type="text", text=result)]


async def _run_server():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Sync entry point (used by the `kademcp` console script and `python3 server.py`)."""
    asyncio.run(_run_server())


if __name__ == "__main__":
    main()
