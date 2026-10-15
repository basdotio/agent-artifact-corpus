#!/usr/bin/env python3

import argparse
import asyncio
import os
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types


def extract_server_name_from_url(url: str) -> str:
    """Extract a server name from the URL."""
    parsed = urlparse(url)
    hostname = parsed.hostname or "unknown"

    # For vercel.app URLs, extract the subdomain
    if hostname.endswith(".vercel.app"):
        subdomain = hostname[:-11]  # Remove '.vercel.app'
        return subdomain

    # Fallback for other URLs
    return hostname.replace(".", "_").replace("-", "_")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Bridge MCP requests to a remote MCP server",
    )

    parser.add_argument(
        "endpoint",
        help="Remote MCP server URL",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (outputs tool names to stdout)",
    )

    return parser.parse_args()


class RemoteMCPBridge:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key = os.environ.get("MCP_API_KEY")

    async def forward_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Forward MCP requests to the remote server."""
        request_data = {"jsonrpc": "2.0", "method": method, "id": 1}
        if params:
            request_data["params"] = params

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        # Add API key if available
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            # Use the /mcp endpoint path
            url = f"{self.endpoint}/mcp"
            response = await self.client.post(
                url,
                json=request_data,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Bridge error: {str(e)}"},
                "id": 1,
            }


async def main():
    # Parse command line arguments inside main() to avoid early exit
    args = parse_arguments()
    REMOTE_ENDPOINT = args.endpoint.rstrip("/")  # Remove trailing slash if present

    # Extract server name from URL
    SERVER_NAME = extract_server_name_from_url(REMOTE_ENDPOINT)

    # Create the bridge
    bridge = RemoteMCPBridge(REMOTE_ENDPOINT)

    # Create MCP server
    server: Server = Server(SERVER_NAME)

    @server.list_tools()
    async def handle_list_tools() -> List[types.Tool]:
        """List available tools from the remote server."""
        try:
            print(f"Requesting tools from {REMOTE_ENDPOINT}/mcp", file=sys.stderr)
            response = await bridge.forward_request("tools/list")

            if "result" in response and "tools" in response["result"]:
                tools = []
                for tool_data in response["result"]["tools"]:
                    tools.append(
                        types.Tool(
                            name=tool_data["name"],
                            description=tool_data["description"],
                            inputSchema=tool_data["inputSchema"],
                        )
                    )
                print(f"Successfully loaded {len(tools)} tools", file=sys.stderr)
                return tools
            elif "error" in response:
                print(f"Error from endpoint: {response['error']}", file=sys.stderr)
                return []
            else:
                print(f"Unexpected response format: {response}", file=sys.stderr)
                return []
        except Exception as e:
            print(f"Error listing tools: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            return []

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any]
    ) -> List[types.TextContent]:
        """Call a tool on the remote server."""
        try:
            response = await bridge.forward_request(
                "tools/call", {"name": name, "arguments": arguments}
            )

            if "result" in response:
                result = response["result"]
                content_items = []

                for content in result.get("content", []):
                    if content.get("type") == "text":
                        content_items.append(
                            types.TextContent(type="text", text=content["text"])
                        )

                return content_items
            elif "error" in response:
                return [
                    types.TextContent(
                        type="text", text=f"Error: {response['error']['message']}"
                    )
                ]
            else:
                return [types.TextContent(type="text", text="Unknown response format")]

        except Exception as e:
            print(f"Error calling tool {name}: {e}", file=sys.stderr)
            return [types.TextContent(type="text", text=f"Bridge error: {str(e)}")]

    # Run the server using stdio transport immediately
    # Don't do connection tests during startup as they can cause delays
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        # Log startup to stderr (won't interfere with MCP protocol)
        print("Starting MCP Bridge...", file=sys.stderr)
        print(f"Endpoint: {REMOTE_ENDPOINT}", file=sys.stderr)
        print(f"Server name: {SERVER_NAME}", file=sys.stderr)
        print("", file=sys.stderr)

        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=SERVER_NAME,
                server_version="0.1.0",
                capabilities=types.ServerCapabilities(
                    tools=types.ToolsCapability(listChanged=True)
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
