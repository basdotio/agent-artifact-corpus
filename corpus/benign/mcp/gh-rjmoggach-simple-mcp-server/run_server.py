#!/usr/bin/env python
"""
Run script for Simple MCP Server with FastMCP.
"""
import asyncio
import logging
import platform
import sys
import threading

from fastapi import Request
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the port - use 9876 to avoid potential conflicts
PORT = 9876
API_TOKEN = "SIMPLE_MCP_SERVER"


class AuthMiddleware(BaseHTTPMiddleware):
    """Simple Middleware to authenticate API requests using token from headers."""

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for health endpoint
        path = request.url.path
        if path.startswith("/health"):
            return await call_next(request)

        # Get token from header
        auth_header = request.headers.get("Authorization", "")

        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid authorization token")
            return JSONResponse(
                {"detail": "Invalid or missing authorization token"},
                status_code=401,
            )

        token = auth_header.replace("Bearer ", "")
        if token != API_TOKEN:
            logger.warning("Invalid authorization token")
            return JSONResponse(
                {"detail": "Invalid authorization token"},
                status_code=401,
            )
        logger.info("Authorization token is valid")
        # Token is valid, proceed with the request
        return await call_next(request)


def create_mcp_server():
    """Factory function to create MCP server with tools."""
    mcp = FastMCP("Simple MCP Server")

    @mcp.tool()
    async def hello_world(name: str = "World", delay: int = 0) -> dict:
        """A simple hello world tool that returns a greeting.

        Args:
            name: Name to greet
            delay: Optional delay in seconds

        Returns:
            A greeting message
        """
        logger.info(f"hello_world called with name={name}, delay={delay}")
        if delay > 0:
            await asyncio.sleep(delay)
        return {"message": f"Hello, {name}!"}

    @mcp.tool()
    def get_version() -> dict:
        """Get server version information."""
        logger.info("get_version called")
        return {"version": "0.1.0", "name": "Simple MCP Server", "api_version": "FastMCP 2.5.1"}

    @mcp.tool()
    def system_info() -> dict:
        """Get basic system information."""
        logger.info("system_info called")
        return {
            "python_version": platform.python_version(),
            "system": platform.system(),
            "platform": platform.platform(),
        }

    return mcp


def run_http_server():
    """Run HTTP server in a separate thread."""
    mcp_http = create_mcp_server()
    logger.info("Starting HTTP server on port 9876")
    mcp_http.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=PORT,
        path="/",
        middleware=[Middleware(AuthMiddleware)],
    )


def run_stdio_server():
    """Run stdio server in main thread."""
    mcp_stdio = create_mcp_server()
    logger.info("Starting stdio server")
    mcp_stdio.run(transport="stdio")


if __name__ == "__main__":
    if "--http-only" in sys.argv:
        # HTTP only
        run_http_server()
    elif "--stdio-only" in sys.argv:
        # Stdio only
        run_stdio_server()
    else:
        # BOTH simultaneously
        logger.info("Starting Simple MCP Server with BOTH transports")

        # Start HTTP server in background thread
        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()

        # Run stdio in main thread
        run_stdio_server()
