"""Queue-aware facade over the real MCP backend connection.

Wraps a real `MCPBackendClient` so that every operation FastMCP's proxy
layer performs against it is routed through a `CallOrchestrator`,
serializing (or bounding the concurrency of) calls to the real backend.

FastMCP opens `async with client:` around every single backend
touchpoint (tool calls, all discovery, resource reads, prompt renders,
ping, initialize). This facade's own `__aenter__`/`__aexit__` are
no-ops: the one real connection is opened and closed exactly once, for
the lifetime of the app, via the composition root's lifespan hook - not
per call.

This is also where a call is attributed to the client that made it: naming
the caller means reading MCP's request context, which is knowledge the
generic queue below deliberately does not have. The label is handed down to
`CallOrchestrator.submit` as an opaque string.
"""

from __future__ import annotations

import itertools
from collections.abc import MutableMapping
from typing import Any
from weakref import WeakKeyDictionary

from mcp import types as mcp_types

from mcp_call_orchestrator_proxy.interfaces import MCPBackendClient
from mcp_call_orchestrator_proxy.orchestrator import CallOrchestrator


class QueuedMCPBackend:
    """Routes every `MCPBackendClient` call through a `CallOrchestrator`."""

    def __init__(
        self, upstream: MCPBackendClient, orchestrator: CallOrchestrator
    ) -> None:
        self._upstream = upstream
        self._orchestrator = orchestrator

        # Session -> log tag. Weak keys so a disconnecting client's session is
        # still collectable; the counter is what makes the tag *stable*. An
        # id()-derived tag would not be: CPython reuses the address of a freed
        # session, so on an always-on proxy two unrelated clients minutes apart
        # would log under the same name and the attribution would be a lie.
        self._session_tags: MutableMapping[object, str] = WeakKeyDictionary()
        self._session_seq = itertools.count(1)

    def _client_label(self) -> str:
        """Name the client whose request is being served, for log attribution.

        Best-effort by design: discovery calls the proxy makes for itself, and
        anything before a session exists, have no request context. That is not a
        fault, so it degrades to a placeholder rather than raising.
        """
        try:
            from mcp.server.lowlevel.server import request_ctx

            session = request_ctx.get().session
        except (ImportError, LookupError):
            return "no-session"

        tag = self._session_tags.get(session)
        if tag is None:
            params = getattr(session, "client_params", None)
            info = getattr(params, "clientInfo", None)
            name = getattr(info, "name", None) or "client"
            tag = f"{name}-{next(self._session_seq):03d}"
            self._session_tags[session] = tag
        return tag

    async def __aenter__(self) -> QueuedMCPBackend:
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        return None

    async def initialize(self) -> mcp_types.InitializeResult:
        return await self._orchestrator.submit(
            self._upstream.initialize,
            label="initialize",
            client=self._client_label(),
        )

    async def ping(self) -> bool:
        return await self._orchestrator.submit(
            self._upstream.ping, label="ping", client=self._client_label()
        )

    async def list_tools(self) -> list[mcp_types.Tool]:
        return await self._orchestrator.submit(
            self._upstream.list_tools,
            label="list_tools",
            client=self._client_label(),
        )

    async def call_tool_mcp(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        meta: dict[str, Any] | None = None,
    ) -> mcp_types.CallToolResult:
        return await self._orchestrator.submit(
            lambda: self._upstream.call_tool_mcp(name, arguments, meta=meta),
            label=f"call_tool:{name}",
            client=self._client_label(),
        )

    async def list_resources(self) -> list[mcp_types.Resource]:
        return await self._orchestrator.submit(
            self._upstream.list_resources,
            label="list_resources",
            client=self._client_label(),
        )

    async def list_resource_templates(self) -> list[mcp_types.ResourceTemplate]:
        return await self._orchestrator.submit(
            self._upstream.list_resource_templates,
            label="list_resource_templates",
            client=self._client_label(),
        )

    async def read_resource(
        self, uri: str
    ) -> list[mcp_types.TextResourceContents | mcp_types.BlobResourceContents]:
        return await self._orchestrator.submit(
            lambda: self._upstream.read_resource(uri),
            label="read_resource",
            client=self._client_label(),
        )

    async def list_prompts(self) -> list[mcp_types.Prompt]:
        return await self._orchestrator.submit(
            self._upstream.list_prompts,
            label="list_prompts",
            client=self._client_label(),
        )

    async def get_prompt(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> mcp_types.GetPromptResult:
        return await self._orchestrator.submit(
            lambda: self._upstream.get_prompt(name, arguments),
            label=f"get_prompt:{name}",
            client=self._client_label(),
        )
