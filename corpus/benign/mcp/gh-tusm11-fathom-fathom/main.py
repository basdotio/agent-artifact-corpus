"""Fathom MCP server entry point."""

import asyncio
import sys
from mcp.server import Server
from mcp.types import Tool, TextContent, ToolResult
import json
from fathom.mcp_server import FathomMCPServer


async def run_mcp_server():
    """Run Fathom as MCP server."""
    fathom_server = FathomMCPServer()
    server = Server("fathom")

    # Register tool handlers from FathomMCPServer
    @server.list_tools()
    async def list_tools():
        return fathom_server.get_tools()

    # Start server
    async with server:
        print("Fathom MCP server running...", file=sys.stderr)
        await server.wait_for_shutdown()


if __name__ == "__main__":
    asyncio.run(run_mcp_server())
