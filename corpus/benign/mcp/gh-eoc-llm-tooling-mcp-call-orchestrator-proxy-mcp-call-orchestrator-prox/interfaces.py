"""Core interfaces (Protocols) to enable dependency inversion and testability.

Decouples the queuing facade from the concrete MCP client implementation
(a real `fastmcp.client.Client` or a test fake).
"""

from __future__ import annotations

from typing import Any, Protocol

from mcp import types as mcp_types


class MCPBackendClient(Protocol):
    """Structural protocol for the backend object FastMCP's proxy layer drives.

    Mirrors the subset of `fastmcp.client.Client`'s public surface that
    `fastmcp.server.providers.proxy` actually calls: tool calls, all
    discovery methods, resource reads, prompt rendering, ping, and the
    initialize handshake. A real `Client` satisfies this structurally;
    no adapter is required.
    """

    async def __aenter__(self) -> MCPBackendClient: ...

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None: ...

    async def initialize(self) -> mcp_types.InitializeResult:
        """Perform the MCP initialize handshake."""
        ...

    async def ping(self) -> bool:
        """Ping the backend to verify liveness."""
        ...

    async def list_tools(self) -> list[mcp_types.Tool]:
        """Return the list of available tools exactly as discovered upstream."""
        ...

    async def call_tool_mcp(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        meta: dict[str, Any] | None = None,
    ) -> mcp_types.CallToolResult:
        """Execute a tool call and return the raw MCP protocol result."""
        ...

    async def list_resources(self) -> list[mcp_types.Resource]:
        """Return the list of available resources."""
        ...

    async def list_resource_templates(self) -> list[mcp_types.ResourceTemplate]:
        """Return the list of available resource templates."""
        ...

    async def read_resource(
        self, uri: str
    ) -> list[mcp_types.TextResourceContents | mcp_types.BlobResourceContents]:
        """Read a resource's contents."""
        ...

    async def list_prompts(self) -> list[mcp_types.Prompt]:
        """Return the list of available prompts."""
        ...

    async def get_prompt(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> mcp_types.GetPromptResult:
        """Render a prompt."""
        ...
