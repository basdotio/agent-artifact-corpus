"""
MCP Server for Now Playing API
Provides a single tool 'now_playing' that returns currently playing song information.
"""
import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.nowplayingapi.platform_wrapper import get_now_playing_info
from src.nowplayingapi.models import server_init_options

# Create the server instance
server = Server("now-playing-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="now_playing",
            description="Get currently playing song information from music players",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    """Handle tool calls."""
    if name != "now_playing":
        raise ValueError(f"Unknown tool: {name}")
    
    try:
        # Get the current playing song information
        song_info_list = get_now_playing_info()
        
        # Format the response text
        if song_info_list:
            formatted_songs = []
            for song in song_info_list:
                formatted_songs.append(f"🎵 {song.song_title} (from {song.process_name})")
            
            response_text = "Currently playing:\n" + "\n".join(formatted_songs)
        else:
            response_text = "No music is currently playing."
        
        return [
            TextContent(
                type="text",
                text=response_text
            )
        ]
    
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Error getting now playing information: {str(e)}"
            )
        ]

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server_init_options
        )

if __name__ == "__main__":
    asyncio.run(main())