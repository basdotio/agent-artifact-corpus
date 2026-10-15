"""FastMCP server construction for the proxy.

Wraps the queue-aware backend facade in FastMCP's own `FastMCPProxy`,
which mirrors upstream tools/resources/prompts using their exact
original JSON schema - no lossy `arguments: dict` wrapper.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any, cast

from fastmcp import Client, FastMCP
from fastmcp.server.providers.proxy import FastMCPProxy

from mcp_call_orchestrator_proxy.interfaces import MCPBackendClient


def build_proxy_server(
    backend_factory: Callable[[], MCPBackendClient],
    *,
    server_name: str = "mcp-call-orchestrator-proxy",
    lifespan: Callable[[FastMCP], AbstractAsyncContextManager[None]] | None = None,
) -> FastMCPProxy:
    """Create a FastMCP proxy server that mirrors the backend's exact tool schemas.

    Bypasses `create_proxy()` deliberately: its internal client-factory
    inference treats non-`Client` targets as raw transports to wrap in a
    fresh `ProxyClient`, which would mishandle our queue-aware facade.
    Passing `client_factory` to `FastMCPProxy` directly works because
    every backend touchpoint in `fastmcp.server.providers.proxy` only
    relies on the facade's structural (duck-typed) compatibility with
    `Client`, never an `isinstance` check.
    """
    return FastMCPProxy(
        client_factory=cast(Callable[[], Client[Any]], backend_factory),
        # "warn" (not "raise") so a down backend is skipped in list_tools
        # aggregation instead of failing the whole listing - this keeps the
        # proxy-native backend_status tool discoverable while the backend is
        # absent ("stay connectable, degrade").
        provider_error_strategy="warn",
        name=server_name,
        lifespan=lifespan,
    )
