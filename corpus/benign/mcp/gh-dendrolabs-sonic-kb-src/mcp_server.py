"""MCP server -- exposes sonic-kb tools to Claude Code over stdio.

Thin wrapper: maps TOOL_DEFINITIONS -> mcp.types.Tool, delegates to execute_tool().
All logging goes to stderr (stdout is JSON-RPC).
"""

from __future__ import annotations

import logging
import sys

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .agent._tools import TOOL_DEFINITIONS, execute_tool

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("sonic-kb-mcp")

server = Server("sonic-kb")

_MCP_TOOLS: list[Tool] = [
    Tool(
        name=td.name,
        description=td.description,
        inputSchema=td.parameters,
    )
    for td in TOOL_DEFINITIONS
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return _MCP_TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.info("tool call: %s", name)
    result = execute_tool(name, arguments, tool_call_id="mcp")
    return [TextContent(type="text", text=result.content)]


async def main() -> None:
    logger.info("sonic-kb MCP server starting (stdio)")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
    logger.info("sonic-kb MCP server stopped")
