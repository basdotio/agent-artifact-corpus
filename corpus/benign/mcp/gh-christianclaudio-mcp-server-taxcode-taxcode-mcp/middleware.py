"""Hierarchical middleware for FastMCP 4 Server Composition.

Execution Order:
1. Parent Middleware (Global audit, timing, secret redaction, and global read-only gate).
2. Child Middleware (Domain-specific guards, bulk-destructive gating, and parameter limits).
3. Tool Handler (Core business logic).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Collection
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import Tool

from taxcode_mcp.config import settings
from taxcode_mcp.errors import SafetyViolationError, redact_secrets
from taxcode_mcp.profiles import is_read_only_tool

logger = logging.getLogger(__name__)

# Synthetic discovery proxies that may wrap a real tool name in arguments.
_SEARCH_PROXY_TOOLS = {"call_tool"}


def _resolve_effective_tool_name(context: MiddlewareContext) -> str:
    """Return the tool name under enforcement, unwrapping search ``call_tool`` proxies."""
    message = context.message
    tool_name = getattr(message, "name", "") if message else ""
    if tool_name not in _SEARCH_PROXY_TOOLS or message is None:
        return tool_name

    arguments = getattr(message, "arguments", None)
    if not isinstance(arguments, dict):
        return tool_name

    nested = arguments.get("name")
    if isinstance(nested, str) and nested:
        return nested
    return tool_name


class ParentAuditMiddleware(Middleware):
    """Global gateway middleware logging operation timing, method, and sanitizing errors."""

    async def on_message(
        self,
        context: MiddlewareContext,
        call_next: Callable[[MiddlewareContext], Any],
    ) -> Any:
        """Intercept request, track timing, log lifecycle, and redact sensitive output."""
        start_time = time.perf_counter()
        method = getattr(context, "method", "unknown")
        tool_name = getattr(context.message, "name", None) if context.message else None
        target = f"{method}:{tool_name}" if tool_name else method

        logger.debug("→ MCP Request received: %s", target)
        try:
            result = await call_next(context)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.debug("← MCP Request completed: %s in %.2fms", target, duration_ms)
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            sanitized_msg = redact_secrets(str(exc))
            logger.error(
                "✗ MCP Request failed: %s in %.2fms: %s", target, duration_ms, sanitized_msg
            )
            if hasattr(exc, "args") and exc.args:
                exc.args = tuple(
                    redact_secrets(str(a)) if isinstance(a, str) else a for a in exc.args
                )
            raise


def _read_only_refusal(name: str) -> SafetyViolationError:
    """Build the read-only refusal for ``name`` (a FastMCP ``ToolError``: ``isError: true``)."""
    return SafetyViolationError(
        f"Server running in read-only mode; tool '{name}' blocked "
        "(not annotated readOnlyHint=True)."
    )


class ReadOnlyGateMiddleware(Middleware):
    """Refuse calls to real tools not annotated ``readOnlyHint=True`` while read-only is on.

    Read-only is on when ``settings.MCP_READONLY`` is set or the gate is built with
    ``enforce=True`` (the ``readonly`` profile). Classification uses only the MCP
    ``readOnlyHint`` annotation of the resolved tool: a missing annotation or
    ``readOnlyHint`` other than ``True`` is a write and is refused (fail closed).

    A name that is not a tool on this server is not refused here: it passes through so
    FastMCP returns its normal ``Unknown tool`` error, and a typo is never reported as an
    existing tool. ``catalog`` holds the profile's tool names captured before the
    read-only filter hid the writes, so a hidden real tool is still refused, not unknown.
    The ``call_tool`` proxy gets the same check: it is unwrapped only when it is a real
    tool on this server (Tool Search attached).
    """

    def __init__(self, enforce: bool = False, catalog: Collection[str] = ()) -> None:
        self.enforce = enforce
        self.catalog = frozenset(catalog)

    async def on_message(
        self,
        context: MiddlewareContext,
        call_next: Callable[[MiddlewareContext], Any],
    ) -> Any:
        """Block non-read-only tool calls before they reach tool handlers.

        1. No serving FastMCP context: the annotation cannot be read, so refuse.
        2. Outer name is ``call_tool`` but not a tool on this server (no Tool Search):
           pass through, so FastMCP reports ``Unknown tool: 'call_tool'``.
        3. Otherwise resolve the effective name (``call_tool`` unwrapped to the proxied
           tool) and refuse it only if it is a real tool not annotated read-only.
        """
        readonly = self.enforce or settings.MCP_READONLY
        if not readonly or getattr(context, "method", None) != "tools/call":
            return await call_next(context)

        fastmcp_context = context.fastmcp_context
        if fastmcp_context is None:
            raise _read_only_refusal(_resolve_effective_tool_name(context))
        server = fastmcp_context.fastmcp

        outer_name = getattr(context.message, "name", "")
        if outer_name in _SEARCH_PROXY_TOOLS:
            _, proxy_known = await self._lookup(server, outer_name)
            if not proxy_known:
                return await call_next(context)

        effective_name = _resolve_effective_tool_name(context)
        tool, known = await self._lookup(server, effective_name)
        if known and not is_read_only_tool(tool):
            raise _read_only_refusal(effective_name)
        return await call_next(context)

    async def _lookup(self, server: FastMCP, name: str) -> tuple[Tool | None, bool]:
        """Resolve ``name`` with the public ``get_tool``; return ``(tool, is_real_tool)``.

        ``get_tool`` returns ``None`` for an unknown name and for a tool hidden by the
        read-only filter; the recorded ``catalog`` tells the two apart.
        """
        tool = await server.get_tool(name)
        return tool, tool is not None or name in self.catalog


class StatutesDomainGuardMiddleware(Middleware):
    """Child domain middleware mounted on statutes sub-server for bulk and mutation protection."""

    async def on_message(
        self,
        context: MiddlewareContext,
        call_next: Callable[[MiddlewareContext], Any],
    ) -> Any:
        """Enforce domain safety gates strictly within the statutes namespace."""
        tool_name = getattr(context.message, "name", "") if context.message else ""
        if tool_name in ("bulk_delete_statutes", "statutes_bulk_delete_statutes"):
            if not settings.MCP_ALLOW_BULK_DESTRUCTIVE:
                raise SafetyViolationError(
                    "Bulk destructive operations disabled. "
                    "Set TAXCODE_MCP_ALLOW_BULK_DESTRUCTIVE=1."
                )

        return await call_next(context)
