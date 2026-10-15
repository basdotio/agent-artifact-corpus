"""
WebSocket-based MCP Server for network connections
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
import websockets
from websockets.server import WebSocketServerProtocol

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.types import (
    JSONRPCMessage,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
)

from .server import HeadlessPMMCPServer

logging.basicConfig(level=logging.INFO, format='[MCP-WS] %(message)s')
logger = logging.getLogger("headless-pm-mcp-ws")


class WebSocketMCPServer(HeadlessPMMCPServer):
    """WebSocket-based MCP Server for network connections."""
    
    def __init__(self, base_url: str = "http://localhost:6969", port: int = 6968):
        super().__init__(base_url)
        self.port = port
        self.clients: Dict[str, WebSocketServerProtocol] = {}
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket client connection."""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.clients[client_id] = websocket
        logger.info(f"Client connected: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    # Parse JSON-RPC message
                    data = json.loads(message)
                    
                    if isinstance(data, dict) and "jsonrpc" in data:
                        # Handle JSON-RPC request
                        response = await self.handle_jsonrpc(data)
                        if response:
                            await websocket.send(json.dumps(response))
                    else:
                        # Handle MCP protocol messages
                        # Convert WebSocket message to MCP protocol format
                        if "method" in data:
                            # This is a method call
                            if data["method"] == "initialize":
                                response = await self.handle_initialize(data)
                            elif data["method"] == "tools/list":
                                response = await self.handle_list_tools()
                            elif data["method"] == "tools/call":
                                response = await self.handle_call_tool(data["params"])
                            elif data["method"] == "resources/list":
                                response = await self.handle_list_resources()
                            elif data["method"] == "resources/read":
                                response = await self.handle_read_resource(data["params"])
                            else:
                                response = {"error": f"Unknown method: {data['method']}"}
                            
                            await websocket.send(json.dumps(response))
                        
                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error",
                            "data": str(e)
                        },
                        "id": None
                    }
                    await websocket.send(json.dumps(error_response))
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e)
                        },
                        "id": data.get("id") if isinstance(data, dict) else None
                    }
                    await websocket.send(json.dumps(error_response))
        
        except websockets.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        finally:
            del self.clients[client_id]
    
    async def handle_jsonrpc(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle JSON-RPC request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            # Route to appropriate handler based on method
            if method == "initialize":
                result = await self.handle_initialize(params)
            elif method == "tools/list":
                result = await self.handle_list_tools()
            elif method == "tools/call":
                result = await self.handle_call_tool(params)
            elif method == "resources/list":
                result = await self.handle_list_resources()
            elif method == "resources/read":
                result = await self.handle_read_resource(params)
            else:
                raise ValueError(f"Method not found: {method}")
            
            # Return JSON-RPC response
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
        
        except Exception as e:
            logger.error(f"Error in JSON-RPC handler: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": request_id
            }
    
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization."""
        return {
            "protocolVersion": "0.1.0",
            "capabilities": {
                "tools": {},
                "resources": {}
            },
            "serverInfo": {
                "name": "headless-pm",
                "version": "1.0.0"
            }
        }
    
    async def run_websocket_server(self):
        """Run the WebSocket server."""
        logger.info(f"Starting WebSocket MCP server on port {self.port}")
        async with websockets.serve(self.handle_client, "0.0.0.0", self.port):
            logger.info(f"MCP WebSocket server running on ws://localhost:{self.port}")
            await asyncio.Future()  # Run forever


async def main():
    """Main entry point for WebSocket server."""
    import sys
    import os
    
    # Get configuration from environment
    base_url = os.getenv('HEADLESS_PM_URL', 'http://localhost:6969')
    port = int(os.getenv('MCP_WS_PORT', '6968'))
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    logger.info(f"Starting WebSocket MCP server on port {port}, API at {base_url}")
    server = WebSocketMCPServer(base_url, port)
    await server.run_websocket_server()


if __name__ == "__main__":
    asyncio.run(main())