#!/usr/bin/env python3
"""
MCP Adapter for Vercel - Converts FastMCP to FastAPI with stateless HTTP handling.
"""

import json
import os
from typing import Any, Dict, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastmcp import FastMCP, Client
from pathlib import Path


def check_api_key(request: Request) -> bool:
    """Check if the request has a valid API key when authentication is enabled"""
    required_api_key = os.environ.get("MCP_API_KEY")

    # If no API key is set in environment, allow all requests
    if not required_api_key:
        return True

    # Check for API key in headers
    provided_key = request.headers.get("X-API-Key") or request.headers.get(
        "Authorization"
    )

    # Handle Bearer token format
    if provided_key and provided_key.startswith("Bearer "):
        provided_key = provided_key[7:]  # Remove "Bearer " prefix

    return provided_key == required_api_key


async def get_tools_from_mcp(mcp: FastMCP) -> List[Dict[str, Any]]:
    """Extract tool information from FastMCP using public API"""
    async with Client(mcp) as client:
        mcp_tools = await client.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": tool.inputSchema,
            }
            for tool in mcp_tools
        ]


async def call_mcp_tool(
    mcp: FastMCP, tool_name: str, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Call a tool using FastMCP's public API"""
    try:
        async with Client(mcp) as client:
            result = await client.call_tool(tool_name, arguments)

            content = [
                (
                    {"type": "text", "text": item.text}
                    if hasattr(item, "text")
                    else {"type": "text", "text": str(item)}
                )
                for item in result
            ]

            return {"content": content, "isError": False}

    except Exception as e:
        return {"error": {"code": -32603, "message": str(e)}}


async def handle_mcp_method(
    mcp: FastMCP, method: str, params: Dict[str, Any], request_id: Any
) -> Dict[str, Any]:
    """Handle MCP methods using FastMCP's public API"""

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": mcp.name, "version": "1.0.0"},
            },
        }

    elif method == "tools/list":
        tools_data = await get_tools_from_mcp(mcp)
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools_data}}

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "Missing tool name"},
            }

        result = await call_mcp_tool(mcp, tool_name, arguments)

        if "error" in result:
            return {"jsonrpc": "2.0", "id": request_id, "error": result["error"]}
        else:
            return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}

    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"},
        }


def build_app(mcp: FastMCP) -> FastAPI:
    """Build a FastAPI app from a FastMCP server for Vercel deployment"""

    app = FastAPI(title=f"{mcp.name} - Vercel Adapter")

    @app.get("/")
    async def read_root():
        """Root endpoint with FastMCP reflection info"""
        tools_data = await get_tools_from_mcp(mcp)
        return {
            "message": f"{mcp.name} is running",
            "status": "ok",
            "server_name": mcp.name,
            "tools_count": len(tools_data),
            "available_tools": [tool["name"] for tool in tools_data],
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        import datetime

        return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

    @app.get("/bridge.py")
    async def serve_bridge_script():
        """Serve the bridge.py script for direct execution with uv run"""
        try:
            # Read the bridge.py file from the project root
            bridge_script_path = Path(__file__).parent.parent / "bridge.py"
            if bridge_script_path.exists():
                content = bridge_script_path.read_text()
                return PlainTextResponse(
                    content=content,
                    media_type="text/plain",
                    headers={"Content-Disposition": "attachment; filename=bridge.py"},
                )
            else:
                return PlainTextResponse(
                    content="# Bridge script not found", status_code=404
                )
        except Exception as e:
            return PlainTextResponse(
                content=f"# Error loading bridge script: {e}", status_code=500
            )

    @app.get("/install.py")
    async def serve_install_script(request: Request):
        """Serve the install.py script with dynamically injected server URL"""
        try:
            # Get the server URL from the request
            server_url = f"{request.url.scheme}://{request.url.netloc}"

            # Read the install.py file from the api directory
            install_script_path = Path(__file__).parent / "install.py"
            if install_script_path.exists():
                content = install_script_path.read_text()

                # Inject the server URL into the script
                # Replace a placeholder with the actual server URL
                injected_content = content.replace(
                    "# INJECTED_SERVER_URL = None",
                    f"INJECTED_SERVER_URL = '{server_url}'",
                )

                return PlainTextResponse(
                    content=injected_content,
                    media_type="text/plain",
                    headers={"Content-Disposition": "attachment; filename=install.py"},
                )
            else:
                return PlainTextResponse(
                    content="# Install script not found", status_code=404
                )
        except Exception as e:
            return PlainTextResponse(
                content=f"# Error loading install script: {e}", status_code=500
            )

    @app.post("/mcp")
    async def handle_mcp_request(request: Request):
        """Handle MCP JSON-RPC requests using FastMCP's public API"""
        try:
            if not check_api_key(request):
                raise HTTPException(status_code=403, detail="API key is required")

            body = await request.body()
            request_data = json.loads(body.decode())

            method = request_data.get("method")
            params = request_data.get("params", {})
            request_id = request_data.get("id")

            response = await handle_mcp_method(mcp, method, params, request_id)
            return JSONResponse(content=response)

        except json.JSONDecodeError:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            return JSONResponse(content=error_response, status_code=400)

        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": request_data.get("id") if "request_data" in locals() else None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            }
            return JSONResponse(content=error_response, status_code=500)

    return app
