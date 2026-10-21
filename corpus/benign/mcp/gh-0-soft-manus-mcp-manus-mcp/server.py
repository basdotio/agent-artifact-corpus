"""MCP server bootstrap: wires ManusClient + registered tools into an MCP Server."""

from __future__ import annotations

import json
from typing import Any

from mcp import types
from mcp.server.lowlevel import Server
from pydantic import BaseModel, ValidationError

from manus_mcp import __version__
from manus_mcp.client import ManusApiError, ManusClient, ManusNetworkError
from manus_mcp.client.rate_limiter import RateLimiter
from manus_mcp.client.retry import RetryPolicy
from manus_mcp.config import Settings
from manus_mcp.logger import get_logger
from manus_mcp.tools import ToolCtx, ToolDef, all_tools, load_all_tool_modules

_LOG = get_logger("server")


def _input_schema_for(model: type[BaseModel]) -> dict[str, Any]:
    """Return a JSON Schema suitable for MCP Tool.inputSchema."""
    schema = model.model_json_schema()
    if schema.get("type") != "object":
        # Pydantic always returns "object" for BaseModel, but be defensive.
        schema = {"type": "object", "properties": {}, "allOf": [schema]}
    return schema


def list_registered_tools() -> list[types.Tool]:
    """Return the static list of MCP tools surfaced to clients."""
    return [
        types.Tool(
            name=t.name,
            description=t.description,
            inputSchema=_input_schema_for(t.input_schema),
        )
        for t in all_tools()
    ]


async def dispatch_tool_call(
    name: str,
    arguments: dict[str, Any],
    *,
    tools_by_name: dict[str, ToolDef[Any, Any]],
    ctx: ToolCtx,
) -> list[types.ContentBlock]:
    """Pure dispatch function: validate input, call handler, map errors to MCP content.

    Exposed for direct unit-testing without the `mcp.server.lowlevel.Server` decorator
    which adds its own framework-level validation.
    """
    tool = tools_by_name.get(name)
    if tool is None:
        raise ValueError(f"Unknown tool: {name}")

    try:
        validated = tool.input_schema.model_validate(arguments or {})
    except ValidationError as e:
        return [types.TextContent(type="text", text=f"invalid_argument: {e}")]

    try:
        result = await tool.handler(validated, ctx)
    except ManusApiError as e:
        return [types.TextContent(type="text", text=str(e))]
    except ManusNetworkError as e:
        return [types.TextContent(type="text", text=f"network_error: {e}")]
    except Exception as e:
        _LOG.exception("Tool %s failed", name)
        return [types.TextContent(type="text", text=f"internal_error: {e}")]

    payload = result.model_dump(mode="json", exclude_none=True)
    return [types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]


def build_server(settings: Settings) -> tuple[Server, ManusClient]:
    """Construct the MCP Server wired to a ManusClient. Caller drives the transport."""
    load_all_tool_modules()
    tools = all_tools()
    _LOG.info("Registering %d tools", len(tools))

    client = ManusClient(
        api_key=settings.manus_api_key,
        base_url=settings.manus_base_url,
        timeout=settings.manus_http_timeout,
        rate_limiter=RateLimiter(),
        retry_policy=RetryPolicy(),
    )
    ctx = ToolCtx(client=client)
    tools_by_name = {t.name: t for t in tools}

    server: Server = Server(name="manus-mcp", version=__version__)

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return list_registered_tools()

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[types.ContentBlock]:
        return await dispatch_tool_call(name, arguments, tools_by_name=tools_by_name, ctx=ctx)

    return server, client
