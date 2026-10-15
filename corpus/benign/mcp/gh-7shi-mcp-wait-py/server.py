from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
import asyncio

server = Server("mcp-server-py")

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(server.name)

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="wait_seconds",
            description="Wait for a specified number of seconds",
            inputSchema={
                "type": "object",
                "required": ["seconds"],
                "properties": {
                    "seconds": {
                        "type": "number",
                        "description": "Number of seconds to wait",
                    }
                },
            },
        )
    ]

@server.call_tool()
async def fetch_tool(
    name: str, arguments: dict
) -> list[types.TextContent]:
    if name != "wait_seconds":
        raise ValueError(f"Unknown tool: {name}")
    if "seconds" not in arguments:
        raise ValueError("Missing required argument 'seconds'")
    seconds = arguments["seconds"]
    await asyncio.sleep(seconds)
    return [types.TextContent(type="text", text=f"Waited for {seconds} seconds")]

async def run():
    try:
        # Run the server as STDIO
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=server.name,
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    )
                )
            )
    except Exception as e:
        logger.error(f"Error: {e}")
    logger.debug("Server exited")

if __name__ == "__main__":
    asyncio.run(run())
