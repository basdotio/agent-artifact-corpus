"""Discovery-observing audit for exposure-control filter name mismatches (S-4).

Wraps an ``MCPBackendClient`` and, on first successful discovery per surface,
compares the *resolved* filter names against the backend's real listing.
Emits at most one WARNING per ``(surface, name)`` per process. Never filters
or rejects calls — visibility enforcement lives above this layer.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from mcp import types as mcp_types

from mcp_call_orchestrator_proxy.exposure import (
    BACKEND_STATUS_TOOL_NAME,
    PolicyMode,
    ResolvedPolicy,
    Surface,
)
from mcp_call_orchestrator_proxy.interfaces import MCPBackendClient

logger = logging.getLogger(__name__)


class ExposureAuditBackend:
    """Decorator that audits filter names against real discovery listings."""

    def __init__(
        self,
        upstream: MCPBackendClient,
        policies: Mapping[Surface, ResolvedPolicy],
    ) -> None:
        self._upstream = upstream
        self._policies = policies
        self._warned: set[tuple[Surface, str]] = set()
        # None = that listing has not succeeded yet (resource union waits for both).
        self._seen_resource_uris: set[str] | None = None
        self._seen_template_uris: set[str] | None = None

    async def __aenter__(self) -> ExposureAuditBackend:
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        return None

    async def initialize(self) -> mcp_types.InitializeResult:
        return await self._upstream.initialize()

    async def ping(self) -> bool:
        return await self._upstream.ping()

    async def list_tools(self) -> list[mcp_types.Tool]:
        result = await self._upstream.list_tools()
        real = {t.name for t in result} | {BACKEND_STATUS_TOOL_NAME}
        self._check_simple(Surface.TOOL, real)
        return result

    async def call_tool_mcp(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        meta: dict[str, Any] | None = None,
    ) -> mcp_types.CallToolResult:
        return await self._upstream.call_tool_mcp(name, arguments, meta=meta)

    async def list_resources(self) -> list[mcp_types.Resource]:
        result = await self._upstream.list_resources()
        self._seen_resource_uris = {str(r.uri) for r in result}
        self._maybe_check_resources()
        return result

    async def list_resource_templates(self) -> list[mcp_types.ResourceTemplate]:
        result = await self._upstream.list_resource_templates()
        self._seen_template_uris = {t.uriTemplate for t in result}
        self._maybe_check_resources()
        return result

    async def read_resource(
        self, uri: str
    ) -> list[mcp_types.TextResourceContents | mcp_types.BlobResourceContents]:
        return await self._upstream.read_resource(uri)

    async def list_prompts(self) -> list[mcp_types.Prompt]:
        result = await self._upstream.list_prompts()
        self._check_simple(Surface.PROMPT, {p.name for p in result})
        return result

    async def get_prompt(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> mcp_types.GetPromptResult:
        return await self._upstream.get_prompt(name, arguments)

    def _check_simple(self, surface: Surface, real: set[str]) -> None:
        if self._policies[surface].mode == PolicyMode.UNSET:
            return
        self._emit_misses(surface, real)

    def _maybe_check_resources(self) -> None:
        if self._policies[Surface.RESOURCE].mode == PolicyMode.UNSET:
            return
        if self._seen_resource_uris is None or self._seen_template_uris is None:
            return
        real = self._seen_resource_uris | self._seen_template_uris
        self._emit_misses(Surface.RESOURCE, real)

    def _emit_misses(self, surface: Surface, real: set[str]) -> None:
        referenced = self._policies[surface].names
        for name in sorted(referenced - real):
            key = (surface, name)
            if key in self._warned:
                continue
            self._warned.add(key)
            logger.warning(
                "exposure: %s filter name %r not found on backend",
                surface.value,
                name,
            )
