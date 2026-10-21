"""The MCP servers behind the Gateway, and the connections it holds to them.

Each server is a child process of the Gateway speaking MCP over its stdin/stdout. None of
them opens a network port, so nothing but the Gateway can reach them, wherever it runs.
"""

import os
import sys
from collections.abc import AsyncGenerator, Mapping
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass

from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, Tool

# Environment variables a downstream server is given. Everything else the Gateway has
# (keys, tokens) stays with the Gateway.
PASSED_ENVIRONMENT = ("DATABASE_URL",)

SERVERS: Mapping[str, list[str]] = {
    "accounts": ["-m", "mcp_guard.fake_servers.accounts"],
}


@dataclass(frozen=True)
class Downstream:
    """Open connections to the downstream servers, and which server owns each tool."""

    tools: list[Tool]
    _clients: Mapping[str, Client]

    def owns(self, tool_name: str) -> bool:
        return tool_name in self._clients

    async def call_tool(self, name: str, arguments: dict[str, object] | None) -> CallToolResult:
        return await self._clients[name].call_tool(name, arguments)


@asynccontextmanager
async def connect() -> AsyncGenerator[Downstream]:
    """Start every downstream server, list its tools, and stop them all on exit."""
    environment = {name: os.environ[name] for name in PASSED_ENVIRONMENT if name in os.environ}
    tools: list[Tool] = []
    clients: dict[str, Client] = {}
    async with AsyncExitStack() as stack:
        for name, args in SERVERS.items():
            params = StdioServerParameters(command=sys.executable, args=args, env=environment)
            # No response cache: the Gateway must always see a server's current definitions.
            client = await stack.enter_async_context(Client(params, cache=None))
            for tool in await _all_tools(client):
                if tool.name in clients:
                    raise ValueError(f"Tool {tool.name!r} from {name!r} is already defined")
                tools.append(tool)
                clients[tool.name] = client
        yield Downstream(tools, clients)


async def _all_tools(client: Client) -> list[Tool]:
    tools: list[Tool] = []
    cursor: str | None = None
    while True:
        page = await client.list_tools(cursor=cursor)
        tools += page.tools
        cursor = page.next_cursor
        if cursor is None:
            return tools
