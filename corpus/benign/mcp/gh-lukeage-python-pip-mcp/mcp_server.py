# mcp_server.py
import asyncio
from datetime import datetime
import sys
import os
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Create server instance
server = Server("date-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="get-datetime",
            description="Get the current date and time",
            inputSchema={
                "type": "object",
                "properties": {},  # No input needed
                "required": []
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution"""
    if name == "get-datetime":
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return [
            types.TextContent(
                type="text",
                text=f"Current date and time: {current_time}"
            )
        ]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    """Run the server"""
    # Set binary mode for stdin/stdout on Windows
    if sys.platform == 'win32':
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="date-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )
        )

if __name__ == "__main__":
    asyncio.run(main())