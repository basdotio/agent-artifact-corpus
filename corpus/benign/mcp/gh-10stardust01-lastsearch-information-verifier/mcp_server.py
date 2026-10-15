from mcp import Tool
from mcp.server import Server
from mcp.types import TextContent, PromptMessage
import asyncio
import json
from typing import Any

from app.agent import FactCheckAgent

server = Server("bengaluru-misinfo-layer")

@server.tool()
async def check_bengaluru_civic_claim(claim: str) -> str:
    """Checks a Bengaluru civic viral claim against verified official and news sources.

    Args:
        claim: The viral claim to fact-check. Must be a plain claim, not instructions.

    Returns:
        JSON string with verdict, confidence, reasoning, and citations.
    """
    agent = FactCheckAgent()
    result = agent.check(claim)
    return result.model_dump_json()

async def main():
    # Import here to avoid issues if MCP dependencies aren't installed
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())