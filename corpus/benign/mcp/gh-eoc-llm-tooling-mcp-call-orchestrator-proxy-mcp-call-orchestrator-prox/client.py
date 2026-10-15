"""Factory for the real backend connection.

fastmcp's own `Client` already handles Bearer auth, self-signed TLS, and
reentrant session lifecycle - no hand-rolled httpx/ClientSession plumbing
needed here.

Two backend sources are supported (see `ProxySettings`):

- A standard ``mcpServers`` JSON config file (`backend_config`). FastMCP's
  ``MCPConfig`` parses and validates it; a single-server config yields a direct
  transport with no tool-name prefixing, preserving exact tool parity. TLS
  verification is applied on top from `backend_verify_tls`, since the standard
  format has no verify field.
- The individual `backend_mcp_url` + `backend_api_key` fields (fallback).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import (
    ClientTransport,
    SSETransport,
    StdioTransport,
    StreamableHttpTransport,
)
from fastmcp.mcp_config import MCPConfig

from mcp_call_orchestrator_proxy.config import ProxySettings


def build_real_backend_client(settings: ProxySettings) -> Client[Any]:
    """Build a fastmcp Client for the configured backend.

    A plain string `auth` is auto-wrapped as Bearer auth by fastmcp;
    `verify=False` disables TLS verification for a self-signed cert.
    `init_timeout` bounds a single connect/initialize attempt so the resilient
    supervisor's retry loop stays responsive when the backend is slow or absent.
    """
    if settings.backend_config:
        transport = _single_server_transport(settings.backend_config)
        kwargs: dict[str, Any] = {
            "timeout": settings.call_timeout_seconds,
            "init_timeout": settings.connect_timeout_seconds,
        }
        # `verify` only applies to HTTP transports; a stdio backend has no TLS.
        if isinstance(transport, StreamableHttpTransport | SSETransport):
            kwargs["verify"] = settings.backend_verify_tls
        return Client(transport, **kwargs)

    return Client(
        settings.backend_mcp_url,
        auth=settings.backend_api_key,
        verify=settings.backend_verify_tls,
        timeout=settings.call_timeout_seconds,
        init_timeout=settings.connect_timeout_seconds,
    )


def _single_server_transport(config_path: str) -> ClientTransport:
    """Load a standard mcpServers JSON file and return its single transport.

    This proxy fronts exactly one backend, so a config that defines more than
    one server is rejected: FastMCP would otherwise mount them as a composite
    and prefix every tool name (`{server}_{tool}`), breaking exact parity.
    """
    config = MCPConfig.from_file(Path(config_path))
    servers = config.mcpServers
    if len(servers) != 1:
        raise ValueError(
            f"Backend config {config_path!r} must define exactly one MCP server "
            f"(this proxy fronts a single backend); found {len(servers)}: "
            f"{sorted(servers)}."
        )
    transport = next(iter(servers.values())).to_transport()
    if isinstance(transport, StdioTransport):
        # `keep_alive=True` (fastmcp's default) is for reusing one subprocess
        # across several separate `async with client:` blocks in a long-lived
        # host process - not this proxy's shape. ResilientBackend builds a
        # fresh client per connection attempt and lets the old one go out of
        # scope on disconnect; with keep_alive left on, that leaves the
        # subprocess running until Python happens to garbage-collect it. This
        # proxy owns a stdio backend's whole life (docs/roadmap.md), so the
        # override is unconditional - regardless of what the config's own
        # `keep_alive` field says - to guarantee no orphaned child survives a
        # reconnect or a shutdown.
        transport.keep_alive = False
    return transport


def resolve_backend_url(settings: ProxySettings) -> str:
    """Human-readable backend URL for the `backend_status` tool.

    In config-file mode the URL lives inside the JSON; fall back to a stdio
    marker for a command-based backend that has no URL.
    """
    if settings.backend_config:
        config = MCPConfig.from_file(Path(settings.backend_config))
        server = next(iter(config.mcpServers.values()))
        return str(getattr(server, "url", None) or f"<stdio:{settings.backend_config}>")
    return settings.backend_mcp_url
