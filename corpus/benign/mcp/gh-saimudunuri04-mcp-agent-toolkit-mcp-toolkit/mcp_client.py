"""MCP client wrapper with scoped permissions.

The agent may only call tools in ``allowed_tools`` (default: all three).
Set MCP_ALLOWED_TOOLS="doc_search,record_lookup" to scope it down.
Connects in-process (tests/dev) or over HTTP via MCP_SERVER_URL.
"""
from __future__ import annotations

import json

from fastmcp import Client


def _result_to_json(result) -> str:
    parts = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


class MCPToolClient:
    def __init__(self, server=None, url: str | None = None,
                 allowed_tools: tuple = ("doc_search", "record_lookup", "text_stats")):
        if server is None and not url:
            raise ValueError("pass a FastMCP server instance or a url")
        self._server = server
        self._url = url
        self.allowed_tools = tuple(allowed_tools)

    def _make_client(self) -> Client:
        return Client(self._server) if self._server is not None else Client(self._url)

    async def list_tools(self) -> list[dict]:
        async with self._make_client() as client:
            tools = await client.list_tools()
        return [{"name": t.name, "description": t.description} for t in tools]

    async def call_tool(self, name: str, args: dict) -> str:
        if name not in self.allowed_tools:
            raise PermissionError(
                f"tool {name!r} is outside the allowed scopes {list(self.allowed_tools)}"
            )
        async with self._make_client() as client:
            result = await client.call_tool(name, args or {})
        text = _result_to_json(result)
        try:
            return json.dumps(json.loads(text))  # normalize
        except Exception:
            return text
