"""A one-tool MCP server: submit_answer, with the schema of the turn being run.

Used when the model is driven through Claude Code, whose agent loop calls MCP tools rather than
the runner's own. The schema comes from BENCH_SUBMIT_TURN (the turn as JSON); a valid submission
is written to BENCH_SUBMIT_OUT, and an invalid one is answered with the same validation message
the runner gives (answer.validate).
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from . import answer


def main() -> None:
    turn = json.loads(os.environ["BENCH_SUBMIT_TURN"])
    out = Path(os.environ["BENCH_SUBMIT_OUT"])
    spec = answer.tool(turn)["function"]
    server = Server("bench")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [types.Tool(name=spec["name"], description=spec["description"], inputSchema=spec["parameters"])]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        error = answer.validate(turn, arguments)
        if error:
            return [types.TextContent(type="text", text=error)]
        out.write_text(json.dumps(arguments))
        return [types.TextContent(type="text", text="Answer recorded.")]

    async def run() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
