#!/usr/bin/env python3
"""
ClickUp MCP Server - Comprehensive implementation of all ClickUp API capabilities.

This file is a thin entrypoint. The tool schemas and request-handling logic
live in the `clickup_mcp` package, organized by ClickUp API area (tasks,
goals, docs, time tracking, ...). See clickup_mcp/tools/__init__.py for the
full list of categories.
"""
import json
from typing import List

import httpx
from mcp.server import Server
from mcp.types import TextContent

from clickup_mcp.tools import CATEGORIES

# Initialize MCP Server
app = Server("clickup-mcp")


@app.list_tools()
async def list_tools():
    """List all available tools, aggregated from every category module."""
    tools = []
    for category in CATEGORIES:
        tools.extend(category.TOOLS)
    return tools


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle a tool call by trying each category's handler in turn.

    Every category module exposes handle(name, arguments) -> Optional[List[TextContent]].
    It returns a result if it owns that tool name, or None so the next
    category gets a chance. This mirrors the single if/elif chain the
    handlers used to share, just split by area.
    """
    try:
        for category in CATEGORIES:
            result = await category.handle(name, arguments)
            if result is not None:
                return result
        return [TextContent(type="text", text=f'{{"error": "Unknown tool: {name}"}}')]

    except httpx.HTTPStatusError as e:
        error_text = f"HTTP Error {e.response.status_code}: {e.response.text}"
        return [TextContent(type="text", text=json.dumps({"error": error_text}, indent=2))]
    except Exception as e:
        error_text = f"Error: {str(e)}"
        return [TextContent(type="text", text=json.dumps({"error": error_text}, indent=2))]


async def main():
    """Main entry point"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
