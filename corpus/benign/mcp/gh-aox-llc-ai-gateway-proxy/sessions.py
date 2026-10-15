"""Upstream connections for tool calls, one set per downstream MCP session.

Each downstream session (one client, bound by the SDK to the credential that opened it)
gets its own connection to each upstream it calls, opened on first use. No upstream
session state, cancellation or server-initiated message can cross from one client to
another. Connections close when the client ends its session (DELETE), when the session
has been idle for the idle timeout, or when the gateway shuts down.

A connection is owned by a dedicated task, because an MCP client must be entered and
exited in the same task. Request handlers only send calls through it.

Identity: every forwarded call carries the gateway's own `_meta`, holding only the
authenticated client's name. A `_meta` the client sent is never forwarded, so a client
cannot claim to be another one. Servers record the name for attribution, never for
authorization.

Retry rule: a broken connection is replaced on the next call, but a call that may have
reached the upstream is never retried; Phase 2 adds tools that write.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast
from uuid import UUID

import anyio
import httpx2
from anyio.abc import TaskGroup, TaskStatus
from mcp.client import Client
from mcp.shared.exceptions import MCPError
from mcp.types import REQUEST_TIMEOUT, CallToolResult, RequestParamsMeta

from ai_gateway.pipeline.runner import UpstreamStatus
from ai_gateway.proxy.upstream_client import UpstreamClientFactory, open_upstream_client
from ai_gateway.registry.models import UpstreamServer
from mcp_common.attribution import CLIENT_META_KEY

logger = logging.getLogger(__name__)

_SWEEP_INTERVAL_S = 30.0

# Lost connections surface as one of these, depending on where in the stack they break.
_CONNECTION_ERRORS = (
    httpx2.HTTPError,
    OSError,
    anyio.BrokenResourceError,
    anyio.ClosedResourceError,
    anyio.EndOfStream,
)


class SessionOwnershipError(Exception):
    """A session id arrived with a different client's credential."""


class UpstreamCallError(Exception):
    def __init__(self, status: UpstreamStatus, namespace: str) -> None:
        super().__init__(f"call to upstream {namespace} failed: {status.value}")
        self.status = status
        self.namespace = namespace


@dataclass
class _Connection:
    upstream: UpstreamServer
    ready: anyio.Event = field(default_factory=anyio.Event)
    close_requested: anyio.Event = field(default_factory=anyio.Event)
    client: Client | None = None
    is_closed: bool = False


@dataclass
class _SessionConnections:
    client_id: UUID
    by_namespace: dict[str, _Connection] = field(default_factory=dict)
    last_used: float = 0.0
    calls_in_flight: int = 0


@dataclass
class UpstreamSessionPool:
    open_client: UpstreamClientFactory = open_upstream_client
    idle_timeout_s: float = 900.0
    clock: Callable[[], float] = time.monotonic
    _sessions: dict[str, _SessionConnections] = field(default_factory=dict, init=False)
    _task_group: TaskGroup | None = field(default=None, init=False)

    async def run(self, *, task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED) -> None:
        """Own every upstream connection until cancelled, then close them all."""
        async with anyio.create_task_group() as task_group:
            self._task_group = task_group
            task_group.start_soon(self._sweep_idle_sessions)
            task_status.started()
            try:
                await anyio.sleep_forever()
            finally:
                self._task_group = None
                for session in self._sessions.values():
                    _request_close_all(session)
                self._sessions.clear()

    async def call_tool(
        self,
        session_id: str | None,
        client_id: UUID,
        upstream: UpstreamServer,
        tool: str,
        arguments: dict[str, Any],
        client_name: str,
    ) -> CallToolResult:
        if session_id is None:
            # No downstream session to attach to: use a connection for this call only.
            async with self.open_client(upstream) as client:
                return await self._send(client, upstream, tool, arguments, client_name)

        session = self._session(session_id, client_id)
        connection = await self._connection(session, upstream)
        session.calls_in_flight += 1
        try:
            if connection.client is None:
                raise UpstreamCallError(UpstreamStatus.UNAVAILABLE, upstream.namespace)
            return await self._send(
                connection.client, upstream, tool, arguments, client_name, connection
            )
        finally:
            session.calls_in_flight -= 1
            session.last_used = self.clock()

    def close_session(self, session_id: str, client_id: UUID) -> None:
        session = self._sessions.get(session_id)
        if session is None or session.client_id != client_id:
            return
        _request_close_all(session)
        del self._sessions[session_id]

    def _session(self, session_id: str, client_id: UUID) -> _SessionConnections:
        session = self._sessions.get(session_id)
        if session is None:
            session = _SessionConnections(client_id=client_id, last_used=self.clock())
            self._sessions[session_id] = session
        elif session.client_id != client_id:
            # The SDK already binds a session to its credential; this is a second wall.
            raise SessionOwnershipError(f"session {session_id[:8]} belongs to another client")
        return session

    async def _connection(
        self, session: _SessionConnections, upstream: UpstreamServer
    ) -> _Connection:
        connection = session.by_namespace.get(upstream.namespace)
        if connection is None or connection.is_closed or connection.upstream != upstream:
            if connection is not None:
                connection.close_requested.set()
            connection = self._open(upstream)
            session.by_namespace[upstream.namespace] = connection

        try:
            with anyio.fail_after(upstream.connect_timeout_s):
                await connection.ready.wait()
        except TimeoutError:
            connection.close_requested.set()
            raise UpstreamCallError(UpstreamStatus.UNAVAILABLE, upstream.namespace) from None
        return connection

    def _open(self, upstream: UpstreamServer) -> _Connection:
        if self._task_group is None:
            raise RuntimeError("UpstreamSessionPool.run() is not active")
        connection = _Connection(upstream)
        self._task_group.start_soon(self._own_connection, connection)
        return connection

    async def _own_connection(self, connection: _Connection) -> None:
        namespace = connection.upstream.namespace
        try:
            async with self.open_client(connection.upstream) as client:
                connection.client = client
                connection.ready.set()
                await connection.close_requested.wait()
        except Exception:
            # The connection is gone whatever the cause; the next call opens a new one.
            # Catching broadly is deliberate: an owner task must never crash the pool.
            logger.warning("connection to upstream %s ended", namespace, exc_info=True)
        finally:
            connection.is_closed = True
            connection.client = None
            connection.ready.set()

    async def _send(
        self,
        client: Client,
        upstream: UpstreamServer,
        tool: str,
        arguments: dict[str, Any],
        client_name: str,
        connection: _Connection | None = None,
    ) -> CallToolResult:
        namespace = upstream.namespace
        try:
            # The SDK's own timeout cancels the upstream request; fail_after is a backstop.
            with anyio.fail_after(upstream.call_timeout_s + 1):
                return await client.call_tool(
                    tool,
                    arguments,
                    read_timeout_seconds=upstream.call_timeout_s,
                    meta=cast(RequestParamsMeta, {CLIENT_META_KEY: client_name}),
                )
        except TimeoutError:
            raise UpstreamCallError(UpstreamStatus.TIMEOUT, namespace) from None
        except MCPError as error:
            status = (
                UpstreamStatus.TIMEOUT if error.code == REQUEST_TIMEOUT else UpstreamStatus.REJECTED
            )
            raise UpstreamCallError(status, namespace) from error
        except _CONNECTION_ERRORS as error:
            if connection is not None:
                connection.close_requested.set()
            raise UpstreamCallError(UpstreamStatus.UNAVAILABLE, namespace) from error
        except RuntimeError as error:
            # The SDK client raises RuntimeError when structured output breaks the tool's
            # declared output schema.
            raise UpstreamCallError(UpstreamStatus.INVALID_RESPONSE, namespace) from error

    def close_idle_sessions(self) -> int:
        """Close the connections of sessions idle for longer than the idle timeout."""
        now = self.clock()
        idle = [
            session_id
            for session_id, session in self._sessions.items()
            if session.calls_in_flight == 0 and now - session.last_used > self.idle_timeout_s
        ]
        for session_id in idle:
            _request_close_all(self._sessions.pop(session_id))
        return len(idle)

    async def _sweep_idle_sessions(self) -> None:
        while True:
            await anyio.sleep(_SWEEP_INTERVAL_S)
            closed = self.close_idle_sessions()
            if closed:
                logger.info("closed upstream connections of %d idle sessions", closed)


def _request_close_all(session: _SessionConnections) -> None:
    for connection in session.by_namespace.values():
        connection.close_requested.set()
