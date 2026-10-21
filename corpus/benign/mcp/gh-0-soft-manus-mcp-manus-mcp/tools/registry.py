"""Decorator-based tool registry used by the MCP server."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from manus_mcp.client import ManusClient

TIn = TypeVar("TIn", bound=BaseModel)
TOut = TypeVar("TOut", bound=BaseModel)


@dataclass
class ToolCtx:
    """Shared runtime context passed to every tool handler."""

    client: ManusClient


ToolHandler = Callable[[Any, ToolCtx], Awaitable[BaseModel]]


@dataclass
class ToolDef(Generic[TIn, TOut]):
    """Metadata + handler for a single MCP tool."""

    name: str
    description: str
    input_schema: type[TIn]
    output_schema: type[TOut]
    handler: Callable[[TIn, ToolCtx], Awaitable[TOut]]
    rate_limit_key: str | None = None


_REGISTRY: dict[str, ToolDef[Any, Any]] = {}


def manus_tool(
    *,
    name: str,
    description: str,
    input_schema: type[TIn],
    output_schema: type[TOut],
    rate_limit_key: str | None = None,
) -> Callable[
    [Callable[[TIn, ToolCtx], Awaitable[TOut]]], Callable[[TIn, ToolCtx], Awaitable[TOut]]
]:
    """Decorator registering `handler` as a tool with the given metadata."""

    def wrap(
        handler: Callable[[TIn, ToolCtx], Awaitable[TOut]],
    ) -> Callable[[TIn, ToolCtx], Awaitable[TOut]]:
        if name in _REGISTRY:
            raise RuntimeError(f"Duplicate tool name: {name}")
        _REGISTRY[name] = ToolDef(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            handler=handler,
            rate_limit_key=rate_limit_key,
        )
        return handler

    return wrap


def all_tools() -> list[ToolDef[Any, Any]]:
    """Return a stable-ordered copy of every registered tool."""
    return sorted(_REGISTRY.values(), key=lambda t: t.name)


def clear_registry() -> None:
    """Test helper."""
    _REGISTRY.clear()
