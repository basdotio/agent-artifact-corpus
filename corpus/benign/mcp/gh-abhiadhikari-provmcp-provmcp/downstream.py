"""Connections to the downstream servers. Shared by the proxy and by replay,
so a replayed call goes through exactly the code path the original did."""

from __future__ import annotations

import logging
import os
import time
from contextlib import AsyncExitStack
from pathlib import Path
from typing import TextIO

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_types import CallToolResult, Tool

from .config import DownstreamServer
from .ledger import canonical, sha256_hex

log = logging.getLogger(__name__)


def result_to_json(result: CallToolResult) -> dict:
    """The exact object the ledger hashes. Alias keys, JSON mode, no None —
    the same shape a client on the wire would see."""
    return result.model_dump(by_alias=True, mode="json", exclude_none=True)


def client_for(server: DownstreamServer, errlog: TextIO | None = None) -> Client:
    """errlog: where a stdio server's stderr goes. Default is our own stderr,
    which is noisy — handshake-era servers log our discover probe as a
    validation error, FastMCP prints a banner. A per-server log file keeps
    the operator's terminal readable and the noise inspectable."""
    if server.inproc is not None:
        return Client(server.inproc)
    if server.command:
        env = {**os.environ, **server.env}
        params = StdioServerParameters(command=server.command[0], args=server.command[1:], env=env)
        if errlog is not None:
            return Client(stdio_client(params, errlog=errlog))
        return Client(params)
    assert server.url
    return Client(server.url)


class Downstreams:
    """Open one client per configured server for the life of the context."""

    def __init__(self, servers: list[DownstreamServer], log_dir: Path | None = None):
        self.servers = {s.id: s for s in servers}
        self.clients: dict[str, Client] = {}
        self.log_dir = Path(log_dir) if log_dir else None
        self._stack: AsyncExitStack | None = None

    async def __aenter__(self) -> Downstreams:
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        if self.log_dir is not None:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        for sid, server in self.servers.items():
            errlog = None
            if self.log_dir is not None and server.command:
                errlog = self._stack.enter_context(
                    (self.log_dir / f"{sid}.stderr.log").open("a", encoding="utf-8")
                )
            client = client_for(server, errlog)
            try:
                await self._stack.enter_async_context(client)
            except Exception:
                log.error("could not connect to downstream server %r", sid)
                await self._stack.aclose()
                raise
            self.clients[sid] = client
            log.info("connected to %r (%s)", sid, client.protocol_version)
        return self

    async def __aexit__(self, *exc: object) -> None:
        assert self._stack is not None
        await self._stack.__aexit__(*exc)
        self.clients.clear()

    async def list_tools(self, server_id: str) -> list[Tool]:
        client = self.clients[server_id]
        tools: list[Tool] = []
        cursor = None
        while True:
            page = await client.list_tools(cursor=cursor)
            tools.extend(page.tools)
            cursor = page.next_cursor
            if not cursor:
                return tools

    async def call(
        self, server_id: str, tool: str, arguments: dict
    ) -> tuple[CallToolResult, dict, int]:
        """Forward one call. Returns (result, result-as-json, duration_ms). Raises
        on transport or protocol failure; a tool-level isError is a normal result."""
        client = self.clients[server_id]
        t0 = time.perf_counter()
        result = await client.call_tool(tool, arguments)
        ms = int((time.perf_counter() - t0) * 1000)
        return result, result_to_json(result), ms


def hash_result(result_json: dict) -> str:
    return sha256_hex(canonical(result_json))


def error_payload(exc: BaseException) -> dict:
    """What gets hashed when the downstream call itself failed. Deterministic
    on the message so a replay that fails the same way still matches."""
    return {"error": f"{type(exc).__name__}: {exc}"}
