#!/usr/bin/env python3
"""
Vercel MCP Server
"""

import datetime
from fastmcp import FastMCP
from .mcp_adapter import build_app

# Create FastMCP server with business logic
mcp: FastMCP = FastMCP("Vercel MCP Server", stateless_http=True, json_response=True)


@mcp.tool()
def echo(message: str) -> str:
    """Echo the provided message back to the user"""
    return f"Tool echo: {message}"


@mcp.tool()
def get_time() -> str:
    """Get the current server time"""
    current_time = datetime.datetime.now().isoformat()
    return f"Current Vercel server time: {current_time}"


@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b


# Build the FastAPI app using the adapter
app = build_app(mcp)

# For local development
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3000)
