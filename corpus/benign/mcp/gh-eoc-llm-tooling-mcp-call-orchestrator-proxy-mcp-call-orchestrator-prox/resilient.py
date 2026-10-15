"""Self-healing backend connection that survives the backend coming and going.

The proxy is meant to run as an always-on ``systemctl --user`` service while the
backend is launched by the user only on demand. So the backend is
routinely *absent at startup* and comes and goes during a session.
``ResilientBackend`` wraps the real backend client behind the ``MCPBackendClient``
protocol and owns a background supervisor task that keeps a single live connection
healthy: connect -> hold open -> on break, back off and retry, forever, until
shutdown.

Design notes:

- Sits *below* the serializing orchestrator (``QueuedMCPBackend`` -> here ->
  real ``fastmcp.Client``), so it never adds concurrency of its own to the
  backend.
- Break detection is **network-silent**: it never runs a timed ping against the
  backend. A dropped connection is signalled by a delegated call failing with a
  connection-type error (the authoritative signal) and, when available, the
  underlying client's ``is_connected()``. Reconnection-after-reappear needs no
  polling either - the backoff retry loop *is* the "wait for it to come back".
- ``initialize()`` never raises just because the backend is down: FastMCP's
  proxy forwards ``initialize`` to us on every client-connect, so raising would
  stop agents from connecting to the proxy at all while the backend is down. We
  return the last-good (or a synthetic) result instead - "stay connectable,
  degrade".
- Shutdown is **prompt**: the backoff sleep is interruptible by the shutdown
  event, so SIGTERM during a long backoff tears down immediately rather than
  stalling systemd's stop timeout.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import anyio
import httpx
from mcp import types as mcp_types
from mcp.shared.exceptions import McpError

from mcp_call_orchestrator_proxy.interfaces import MCPBackendClient

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

# Exceptions that mean "the backend connection is broken", not "a tool failed".
# A failed tool returns CallToolResult(isError=True); only transport/protocol
# problems surface as exceptions here. Mirrors the set FastMCP's own proxy
# treats as upstream errors.
_CONNECTION_ERRORS: tuple[type[BaseException], ...] = (
    RuntimeError,
    TimeoutError,
    httpx.HTTPError,
    anyio.ClosedResourceError,
    anyio.EndOfStream,
    anyio.BrokenResourceError,
)

# A backend that restarts while keeping its HTTP listener up answers any request
# still carrying the now-unknown streamable-HTTP session id with HTTP 404, which
# the MCP SDK surfaces as this JSON-RPC error. That means the session is gone - a
# broken connection to recover from, not a failed call - but it is not one of the
# transport-level exceptions in _CONNECTION_ERRORS, so it is matched on its signal.
_SESSION_TERMINATED_CODE = 32600
_SESSION_TERMINATED_MESSAGE = "Session terminated"

# The SDK's own generic "the session is gone" signal (`mcp.types.CONNECTION_CLOSED`,
# not imported directly to avoid depending on a low-level constant's import path):
# `BaseSession`'s receive loop synthesizes this for every pending request once its
# read stream ends, whatever the transport. That is exactly what a stdio backend's
# dead subprocess produces - the pipe closing is swallowed *inside* the SDK's own
# receive loop and turned into this per-request error, so it never reaches us as one
# of the raw anyio stream errors in _CONNECTION_ERRORS.
_CONNECTION_CLOSED_CODE = -32000


def _is_connection_broken_signal(exc: BaseException) -> bool:
    """True for either of the SDK's two "the session is gone, not just this call
    failed" signals - the generic one and the streamable-HTTP-specific clean-404.

    Deliberately narrow beyond that: an ordinary failed or unknown tool call also
    raises ``McpError``, so matching the whole class would turn a per-call error
    into a full connection teardown.
    """
    if not isinstance(exc, McpError):
        return False
    if exc.error.code == _CONNECTION_CLOSED_CODE:
        return True
    return (
        exc.error.code == _SESSION_TERMINATED_CODE
        and exc.error.message == _SESSION_TERMINATED_MESSAGE
    )


_SYNTHETIC_INIT = mcp_types.InitializeResult(
    protocolVersion=mcp_types.LATEST_PROTOCOL_VERSION,
    capabilities=mcp_types.ServerCapabilities(),
    serverInfo=mcp_types.Implementation(
        name="mcp-call-orchestrator-proxy (backend unavailable)", version="0"
    ),
)


class BackendUnavailableError(RuntimeError):
    """Raised when a backend operation is attempted while the backend is unreachable.

    A ``RuntimeError`` subclass so FastMCP's proxy layer maps it to a clean MCP
    error for the calling client.
    """


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class ResilientBackend:
    """Keeps a single backend connection alive across restarts of the backend.

    Implements ``MCPBackendClient`` so it slots transparently between the
    serializing ``QueuedMCPBackend`` and the real ``fastmcp.Client``. Builds each
    connection from ``factory`` (a fresh client per attempt), which sidesteps any
    stale-session subtleties on reconnect.
    """

    def __init__(
        self,
        factory: Callable[[], MCPBackendClient],
        *,
        backend_url: str = "",
        connect_timeout: float = 30.0,
        initial_backoff: float = 1.0,
        max_backoff: float = 30.0,
        backoff_multiplier: float = 2.0,
        health_poll: float = 5.0,
    ) -> None:
        self._factory = factory
        self._backend_url = backend_url
        self._connect_timeout = connect_timeout
        self._initial_backoff = initial_backoff
        self._max_backoff = max_backoff
        self._multiplier = backoff_multiplier
        self._health_poll = health_poll

        self._live: MCPBackendClient | None = None
        self._last_initialize_result: mcp_types.InitializeResult | None = None

        self._shutdown = asyncio.Event()
        self._broken = asyncio.Event()
        self._first_attempt_done = asyncio.Event()
        self._supervisor_task: asyncio.Task[None] | None = None

        # Status bookkeeping (surfaced by the backend_status tool).
        self._connected_since: datetime.datetime | None = None
        self._last_error: str | None = None
        self._consecutive_failures = 0
        self._current_backoff = 0.0

    # -- lifecycle -----------------------------------------------------------

    async def __aenter__(self) -> ResilientBackend:
        """Start the supervisor and wait for the first connect attempt to resolve.

        Returns once the first attempt has either connected or failed - never
        raising. When the backend is up the connection is ready on return; when it
        is down the supervisor keeps retrying in the background and the proxy
        still starts cleanly.
        """
        self._shutdown.clear()
        self._first_attempt_done = asyncio.Event()
        self._supervisor_task = asyncio.create_task(
            self._supervise(), name="backend-supervisor"
        )
        cap = self._connect_timeout + self._initial_backoff + 5.0
        try:
            await asyncio.wait_for(self._first_attempt_done.wait(), timeout=cap)
        except TimeoutError:
            logger.warning(
                "resilient: first backend connect attempt did not resolve within "
                "%.1fs; continuing in the background",
                cap,
            )
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        """Stop the supervisor promptly and close the live connection."""
        self._shutdown.set()
        task = self._supervisor_task
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=self._connect_timeout + 5.0)
            except TimeoutError:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            self._supervisor_task = None
        self._live = None

    # -- supervisor ----------------------------------------------------------

    async def _supervise(self) -> None:
        """Maintain a live backend connection, reconnecting with bounded backoff."""
        delay = self._initial_backoff
        while not self._shutdown.is_set():
            try:
                client = self._factory()
                async with client:
                    self._last_initialize_result = await client.initialize()
                    self._live = client
                    self._connected_since = _utcnow()
                    failures = self._consecutive_failures
                    self._consecutive_failures = 0
                    self._last_error = None
                    self._current_backoff = 0.0
                    delay = self._initial_backoff
                    if failures:
                        # A recovery is logged at the same severity as the outage
                        # it ends. Otherwise an operator filtering to warnings sees
                        # the backend go down and never sees it come back, and every
                        # transient blip reads as an unresolved incident.
                        logger.warning(
                            "resilient: backend reconnected after %d failed "
                            "attempt(s) - outage over (%s)",
                            failures,
                            self._backend_url,
                        )
                    else:
                        logger.info(
                            "resilient: backend connected (%s)", self._backend_url
                        )
                    self._first_attempt_done.set()
                    await self._hold(client)
            except _CONNECTION_ERRORS as exc:
                self._note_failure(exc, unexpected=False)
            except Exception as exc:
                # The supervisor must never die: log loudly, then retry.
                self._note_failure(exc, unexpected=True)
            finally:
                self._live = None
                self._broken.clear()
                self._first_attempt_done.set()

            if self._shutdown.is_set():
                break
            self._current_backoff = delay
            await self._race(self._shutdown, timeout=self._jitter(delay))
            delay = min(delay * self._multiplier, self._max_backoff)

        logger.debug("resilient: supervisor exiting")

    async def _hold(self, client: MCPBackendClient) -> None:
        """Keep the connection open until it breaks or shutdown is requested.

        Waits on the ``_broken``/``_shutdown`` signals with a local timeout; the
        optional ``is_connected()`` check catches a transport that closed while
        idle. No network traffic is generated against the backend.
        """
        is_connected = getattr(client, "is_connected", None)
        while not self._shutdown.is_set() and not self._broken.is_set():
            if callable(is_connected) and not is_connected():
                break
            await self._race(self._shutdown, self._broken, timeout=self._health_poll)

    def _note_failure(self, exc: BaseException, *, unexpected: bool) -> None:
        self._consecutive_failures += 1
        self._last_error = f"{type(exc).__name__}: {exc}"
        if unexpected:
            logger.exception(
                "resilient: unexpected error in backend supervisor; will retry"
            )
        elif self._consecutive_failures == 1:
            logger.warning("resilient: backend connection failed: %s", self._last_error)
        else:
            logger.debug(
                "resilient: backend still unavailable (attempt %d): %s",
                self._consecutive_failures,
                self._last_error,
            )

    def _jitter(self, delay: float) -> float:
        """Apply +/-20% jitter so repeated retries do not lock-step."""
        return delay * (0.8 + 0.4 * random.random())

    async def _race(self, *events: asyncio.Event, timeout: float) -> None:
        """Return when any event is set or ``timeout`` elapses (whichever first)."""
        waiters = [asyncio.ensure_future(e.wait()) for e in events]
        try:
            await asyncio.wait(
                waiters, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            for w in waiters:
                w.cancel()
            for w in waiters:
                with contextlib.suppress(asyncio.CancelledError):
                    await w

    # -- status --------------------------------------------------------------

    def status_snapshot(self) -> dict[str, Any]:
        """Structured backend-health snapshot for the ``backend_status`` tool."""
        connected = self._live is not None
        return {
            "connected": connected,
            "backend_url": self._backend_url,
            "last_connected_at": (
                self._connected_since.isoformat()
                if self._connected_since is not None
                else None
            ),
            "last_error": None if connected else self._last_error,
            "consecutive_failures": self._consecutive_failures,
            "current_backoff_seconds": self._current_backoff,
        }

    def _unavailable_message(self) -> str:
        base = "Backend is not available"
        return f"{base} at {self._backend_url}" if self._backend_url else base

    def _require_live(self) -> MCPBackendClient:
        client = self._live
        if client is None:
            raise BackendUnavailableError(self._unavailable_message())
        return client

    def _connection_failed(self, exc: BaseException) -> BackendUnavailableError:
        self._broken.set()
        self._last_error = f"{type(exc).__name__}: {exc}"
        return BackendUnavailableError(f"{self._unavailable_message()}: {exc}")

    # -- delegated MCPBackendClient surface ----------------------------------

    async def initialize(self) -> mcp_types.InitializeResult:
        """Return the last-good (or synthetic) init result; never raise when down.

        Populated by the supervisor on connect. Never touches the network here,
        so a client can always complete its initialize handshake with the proxy.
        """
        if self._last_initialize_result is not None:
            return self._last_initialize_result
        return _SYNTHETIC_INIT

    async def _guarded(self, op: Awaitable[_T]) -> _T:
        """Run a delegated backend call, turning a broken connection into a reconnect.

        A transport-level error (``_CONNECTION_ERRORS``) or a connection-broken
        ``McpError`` signal (``_is_connection_broken_signal``) marks the connection
        broken - which wakes the supervisor to tear down and rebuild the client -
        and is re-raised as ``BackendUnavailableError``. Any other error is an
        ordinary per-call failure and propagates unchanged.
        """
        try:
            return await op
        except _CONNECTION_ERRORS as exc:
            raise self._connection_failed(exc) from exc
        except McpError as exc:
            if _is_connection_broken_signal(exc):
                raise self._connection_failed(exc) from exc
            raise

    async def ping(self) -> bool:
        client = self._live
        if client is None:
            return False
        try:
            return await client.ping()
        except _CONNECTION_ERRORS as exc:
            self._connection_failed(exc)
            return False
        except McpError as exc:
            if _is_connection_broken_signal(exc):
                self._connection_failed(exc)
                return False
            raise

    async def list_tools(self) -> list[mcp_types.Tool]:
        client = self._require_live()
        return await self._guarded(client.list_tools())

    async def call_tool_mcp(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        meta: dict[str, Any] | None = None,
    ) -> mcp_types.CallToolResult:
        client = self._require_live()
        return await self._guarded(client.call_tool_mcp(name, arguments, meta=meta))

    async def list_resources(self) -> list[mcp_types.Resource]:
        client = self._require_live()
        return await self._guarded(client.list_resources())

    async def list_resource_templates(self) -> list[mcp_types.ResourceTemplate]:
        client = self._require_live()
        return await self._guarded(client.list_resource_templates())

    async def read_resource(
        self, uri: str
    ) -> list[mcp_types.TextResourceContents | mcp_types.BlobResourceContents]:
        client = self._require_live()
        return await self._guarded(client.read_resource(uri))

    async def list_prompts(self) -> list[mcp_types.Prompt]:
        client = self._require_live()
        return await self._guarded(client.list_prompts())

    async def get_prompt(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> mcp_types.GetPromptResult:
        client = self._require_live()
        return await self._guarded(client.get_prompt(name, arguments))
