import os
import json
import logging
import contextlib
from collections.abc import AsyncIterator

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

from src.mcp.tools import TOOL_DEFS, call_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("taskie-mcp")

server = Server("taskie")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return TOOL_DEFS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.info(f"Tool call: {name}")
    try:
        result = call_tool(name, arguments)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"Tool error: {e}")
        return [TextContent(type="text",
                text=json.dumps({"error": str(e)}))]


session_manager = StreamableHTTPSessionManager(app=server, stateless=True)


async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
    await session_manager.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    async with session_manager.run():
        logger.info("MCP StreamableHTTP session manager started")
        try:
            yield
        finally:
            logger.info("MCP StreamableHTTP session manager shutting down")


# Mount the transport at the root so both `/mcp` and `/mcp/` reach the
# StreamableHTTPSessionManager without Starlette issuing a 307 redirect that
# would break MCP clients pointing at the bare `/mcp` URL documented in the
# README.
app = Starlette(
    debug=False,
    routes=[Mount("/", app=handle_streamable_http)],
    lifespan=lifespan,
)


if __name__ == '__main__':
    import uvicorn
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "5100"))
    logger.info(f"Starting MCP server on http://{host}:{port}/mcp")
    uvicorn.run(app, host=host, port=port, log_level="info")
