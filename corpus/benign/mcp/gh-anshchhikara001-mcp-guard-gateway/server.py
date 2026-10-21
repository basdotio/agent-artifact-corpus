"""The Gateway's MCP server: what an Agent connects to.

It lists the downstream servers' tools as its own and forwards every Tool call, unchanged,
to the server that owns the tool. There is no Decision yet: every call is allowed.

Run it with `make gateway`, or `uv run mcp-guard-gateway` (GATEWAY_HOST and GATEWAY_PORT
pick the address; the default is http://127.0.0.1:8000/mcp).
"""

import os

import uvicorn
from mcp.server import Server, ServerRequestContext
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
)
from starlette.applications import Starlette

from mcp_guard.gateway.downstream import Downstream, connect


async def list_tools(
    ctx: ServerRequestContext[Downstream], params: PaginatedRequestParams | None
) -> ListToolsResult:
    return ListToolsResult(tools=ctx.lifespan_context.tools)


async def call_tool(
    ctx: ServerRequestContext[Downstream], params: CallToolRequestParams
) -> CallToolResult:
    downstream = ctx.lifespan_context
    if not downstream.owns(params.name):
        return CallToolResult(
            content=[TextContent(text=f"Unknown tool: {params.name}")], is_error=True
        )
    return await downstream.call_tool(params.name, params.arguments)


def app(host: str = "127.0.0.1") -> Starlette:
    """The Gateway as an ASGI app, serving MCP over streamable HTTP at /mcp."""
    server = Server[Downstream](
        "mcp-guard",
        lifespan=lambda _: connect(),
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )
    return server.streamable_http_app(host=host)


def main() -> None:
    host = os.environ.get("GATEWAY_HOST", "127.0.0.1")
    port = int(os.environ.get("GATEWAY_PORT", "8000"))
    uvicorn.run(app(host), host=host, port=port)


if __name__ == "__main__":
    main()
