"""Official MCP SDK stdio server. Stdout is reserved for JSON-RPC."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from .documents import TOOL_DEFINITIONS, DocumentStore, ToolError


def create_server(data_dir: Path) -> Server:
    store = DocumentStore(data_dir)
    server = Server("docagent-document-tools", version="1.0.0")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [types.Tool(**definition) for definition in TOOL_DEFINITIONS]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent | types.ImageContent]:
        try:
            result = await asyncio.to_thread(store.call, name, arguments)
            images = result.pop("images", [])
            content = [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
            content.extend(types.ImageContent(type="image", data=item["data"], mimeType=item["mimeType"]) for item in images)
            return content
        except (ToolError, OSError) as exc:
            # Do not expose filesystem paths or exception traces to a tool caller.
            detail = str(exc) if isinstance(exc, ToolError) else "Document I/O failed."
            # SDK 1.12.4 converts handler exceptions to CallToolResult(isError=True).
            raise ToolError(detail) from None

    return server


async def serve(data_dir: Path) -> None:
    server = create_server(data_dir)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve bounded local document tools over MCP stdio.")
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(serve(args.data_dir))


if __name__ == "__main__":
    main()
