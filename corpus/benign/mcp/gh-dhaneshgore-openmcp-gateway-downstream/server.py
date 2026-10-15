"""Client-facing MCP server, built on the SDK's lowlevel `Server` (ADR 0001).

Handlers extract the authenticated principal from the HTTP request, call the
transport-free `GatewayService`, and translate errors into JSON-RPC errors
whose text is always gateway-authored.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable
from typing import Any, TypeVar

import mcp_types as types
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel.server import Server
from mcp.shared.exceptions import MCPError
from mcp_types import INTERNAL_ERROR, INVALID_REQUEST

from openmcp_gateway import __version__
from openmcp_gateway.auth.backends import GatewayUser
from openmcp_gateway.auth.principal import Principal
from openmcp_gateway.errors import GatewayError, UpstreamRpcError
from openmcp_gateway.gateway import GatewayService, ProgressSink

logger = logging.getLogger(__name__)

T = TypeVar("T")
Ctx = ServerRequestContext[Any, Any]


def principal_from(ctx: Ctx) -> Principal:
    request = ctx.request
    user = getattr(request, "user", None) if request is not None else None
    if isinstance(user, GatewayUser):
        return user.principal
    # The auth wrapper on the route rejects unauthenticated HTTP requests, so
    # this only triggers if the server is wired to some other transport.
    raise MCPError(INVALID_REQUEST, "unauthenticated")


async def _guard(awaitable: Awaitable[T]) -> T:
    try:
        return await awaitable
    except GatewayError as exc:
        raise MCPError(exc.code, exc.public_message, exc.data) from None
    except UpstreamRpcError as exc:
        # The upstream's own protocol error is forwarded with its code.
        raise MCPError(exc.code, exc.message, exc.data) from None
    except MCPError:
        raise
    except Exception:
        logger.exception("unhandled error in MCP handler")
        raise MCPError(INTERNAL_ERROR, "internal gateway error") from None


def _progress_sink(ctx: Ctx) -> ProgressSink | None:
    meta: Any = ctx.meta or {}
    token = meta.get("progressToken", meta.get("progress_token")) if isinstance(meta, dict) else None
    if token is None or isinstance(token, bool) or not isinstance(token, str | int):
        return None

    async def sink(progress: float, total: float | None, message: str | None) -> None:
        await ctx.session.send_progress_notification(
            token,
            progress,
            total,
            message,
            related_request_id=str(ctx.request_id) if ctx.request_id is not None else None,
        )

    return sink


def build_mcp_server(service: GatewayService, *, name: str, instructions: str | None = None) -> Server[Any]:
    async def on_list_tools(ctx: Ctx, params: types.PaginatedRequestParams | None) -> types.ListToolsResult:
        tools = await _guard(service.list_tools(principal_from(ctx)))
        return types.ListToolsResult(tools=tools)

    async def on_call_tool(ctx: Ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
        return await _guard(
            service.call_tool(
                principal_from(ctx), params.name, params.arguments, progress=_progress_sink(ctx)
            )
        )

    async def on_list_prompts(
        ctx: Ctx, params: types.PaginatedRequestParams | None
    ) -> types.ListPromptsResult:
        prompts = await _guard(service.list_prompts(principal_from(ctx)))
        return types.ListPromptsResult(prompts=prompts)

    async def on_get_prompt(ctx: Ctx, params: types.GetPromptRequestParams) -> types.GetPromptResult:
        return await _guard(service.get_prompt(principal_from(ctx), params.name, params.arguments))

    async def on_list_resources(
        ctx: Ctx, params: types.PaginatedRequestParams | None
    ) -> types.ListResourcesResult:
        resources = await _guard(service.list_resources(principal_from(ctx)))
        return types.ListResourcesResult(resources=resources)

    async def on_read_resource(ctx: Ctx, params: types.ReadResourceRequestParams) -> types.ReadResourceResult:
        return await _guard(service.read_resource(principal_from(ctx), str(params.uri)))

    return Server(
        name,
        version=__version__,
        instructions=instructions,
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
        on_list_prompts=on_list_prompts,
        on_get_prompt=on_get_prompt,
        on_list_resources=on_list_resources,
        on_read_resource=on_read_resource,
    )
