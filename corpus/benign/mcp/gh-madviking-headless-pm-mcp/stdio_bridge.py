#!/usr/bin/env python3
"""
MCP stdio bridge - connects Claude Code to HTTP MCP server
This acts as a stdio MCP server that proxies to the HTTP MCP server
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    ListResourcesRequest,
    ListResourcesResult,
    ReadResourceRequest,
    ReadResourceResult,
    Tool,
    Resource,
    TextContent,
)

# Disable logging to stderr to avoid interfering with stdio protocol
logging.basicConfig(filename='/tmp/mcp-bridge.log', level=logging.DEBUG)
logger = logging.getLogger("mcp-bridge")


class MCPBridge:
    """Bridge between stdio MCP and HTTP MCP server."""
    
    def __init__(self, http_server_url: str = "http://localhost:6968"):
        self.http_server_url = http_server_url.rstrip('/')
        self.server = Server("headless-pm-bridge")
        self.session_id = f"bridge-{os.getpid()}"
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP handlers that proxy to HTTP server."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """Proxy list tools to HTTP server."""
            try:
                response = await self.client.get(f"{self.http_server_url}/mcp/tools")
                data = response.json()
                
                tools = []
                for tool_data in data.get("tools", []):
                    tools.append(Tool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        inputSchema=tool_data.get("inputSchema", {})
                    ))
                
                return ListToolsResult(tools=tools)
            
            except Exception as e:
                logger.error(f"Error listing tools: {e}")
                return ListToolsResult(tools=[])
        
        @self.server.call_tool()
        async def handle_call_tool(request: CallToolRequest) -> CallToolResult:
            """Proxy tool calls to HTTP server."""
            try:
                # Make HTTP request
                response = await self.client.post(
                    f"{self.http_server_url}/mcp/tools/call",
                    headers={"X-Session-ID": self.session_id},
                    json={
                        "method": request.name,
                        "params": request.arguments,
                        "id": None
                    }
                )
                
                data = response.json()
                
                # Handle error response
                if "error" in data:
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"Error: {data['error'].get('message', 'Unknown error')}"
                            )
                        ]
                    )
                
                # Handle success response
                result = data.get("result", {})
                
                # Convert result to text content
                if isinstance(result, str):
                    text = result
                elif isinstance(result, dict) and "message" in result:
                    text = result["message"]
                else:
                    text = json.dumps(result, indent=2)
                
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=text
                        )
                    ]
                )
            
            except Exception as e:
                logger.error(f"Error calling tool {request.name}: {e}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error: {str(e)}"
                        )
                    ]
                )
        
        @self.server.list_resources()
        async def handle_list_resources() -> ListResourcesResult:
            """Proxy list resources to HTTP server."""
            try:
                response = await self.client.get(f"{self.http_server_url}/mcp/resources")
                data = response.json()
                
                resources = []
                for res_data in data.get("resources", []):
                    resources.append(Resource(
                        uri=res_data["uri"],
                        name=res_data["name"],
                        description=res_data.get("description", ""),
                        mimeType=res_data.get("mimeType", "application/json")
                    ))
                
                return ListResourcesResult(resources=resources)
            
            except Exception as e:
                logger.error(f"Error listing resources: {e}")
                return ListResourcesResult(resources=[])
        
        @self.server.read_resource()
        async def handle_read_resource(request: ReadResourceRequest) -> ReadResourceResult:
            """Proxy read resource to HTTP server."""
            try:
                response = await self.client.post(
                    f"{self.http_server_url}/mcp/resources/read",
                    json={"uri": request.uri}
                )
                
                data = response.json()
                content = data.get("content", {})
                
                return ReadResourceResult(
                    contents=[
                        TextContent(
                            type="text",
                            text=json.dumps(content, indent=2)
                        )
                    ]
                )
            
            except Exception as e:
                logger.error(f"Error reading resource {request.uri}: {e}")
                return ReadResourceResult(
                    contents=[
                        TextContent(
                            type="text",
                            text=f"Error: {str(e)}"
                        )
                    ]
                )
    
    async def run(self):
        """Run the bridge server."""
        try:
            # Initialize HTTP session
            init_response = await self.client.post(
                f"{self.http_server_url}/mcp/initialize",
                headers={"X-Session-ID": self.session_id},
                json={"client": "claude-code-bridge"}
            )
            
            if init_response.status_code != 200:
                logger.error(f"Failed to initialize HTTP session: {init_response.text}")
            
            # Run stdio server
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="headless-pm",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities()
                    )
                )
        finally:
            await self.client.aclose()


async def main():
    """Main entry point."""
    # Get HTTP server URL from environment or command line
    http_server_url = os.getenv('MCP_HTTP_SERVER_URL', 'http://localhost:6968')
    if len(sys.argv) > 1:
        http_server_url = sys.argv[1]
    
    bridge = MCPBridge(http_server_url)
    await bridge.run()


if __name__ == "__main__":
    asyncio.run(main())