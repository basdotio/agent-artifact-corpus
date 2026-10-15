#!/usr/bin/env python3
import asyncio
import json
from datetime import datetime
import pytz
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("daily-uplift-sms")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_current_time",
            description="Get current timestamp for message scheduling",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_message_stats", 
            description="Get real-time message statistics",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_ist_time",
            description="Get current date and time in IST",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_current_time":
        return [TextContent(type="text", text=datetime.now().isoformat())]
    
    elif name == "get_message_stats":
        stats = {
            "total_subscribers": 150,
            "messages_sent_today": 150, 
            "last_message_time": datetime.now().strftime("%H:%M:%S"),
            "categories": ["motivation", "mental_health", "mindfulness"]
        }
        return [TextContent(type="text", text=json.dumps(stats, indent=2))]
    
    elif name == "get_ist_time":
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        ist_time = now_ist.strftime("%A, %d %B %Y %H:%M:%S IST")
        return [TextContent(type="text", text=ist_time)]

async def main():
    async with stdio_server(server) as (read_stream, write_stream):
        await server.run(
            read_stream, 
            write_stream, 
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())