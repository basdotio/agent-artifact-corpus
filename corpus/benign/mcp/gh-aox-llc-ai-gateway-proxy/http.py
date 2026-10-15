"""ASGI wrappers around the SDK's Streamable HTTP endpoint."""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.types import INVALID_REQUEST
from mcp.types.version import HANDSHAKE_PROTOCOL_VERSIONS
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ai_gateway.proxy.sessions import UpstreamSessionPool

logger = logging.getLogger(__name__)

PINNED_PROTOCOL_VERSION = "2025-11-25"
"""The MCP specification revision this gateway is built and tested against."""

ACCEPTED_PROTOCOL_VERSIONS = frozenset(HANDSHAKE_PROTOCOL_VERSIONS)
"""Revisions negotiated through the initialize handshake. The SDK settles on the newest
one the client offers, which is the pinned revision for any current client."""

_PROTOCOL_VERSION_HEADER = "mcp-protocol-version"
_SESSION_ID_HEADER = "mcp-session-id"


class ProtocolVersionGuard:
    """Reject requests that declare a protocol revision the gateway does not speak.

    The SDK would route a 2026-07-28 ("modern", stateless) request to a different code
    path with no sessions, so the per-session upstream handling would not apply. Until a
    later phase adopts that revision, such requests get a clear 400.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        declared = (
            Headers(scope=scope).get(_PROTOCOL_VERSION_HEADER) if scope["type"] == "http" else None
        )
        if declared is None or declared in ACCEPTED_PROTOCOL_VERSIONS:
            await self._app(scope, receive, send)
            return

        logger.info("refused a request declaring MCP protocol version %r", declared[:40])
        body = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": INVALID_REQUEST,
                "message": (
                    f"Unsupported MCP protocol version {declared[:40]!r}."
                    " This gateway uses the initialize handshake and targets"
                    f" {PINNED_PROTOCOL_VERSION}."
                ),
            },
        }
        await send(
            {
                "type": "http.response.start",
                "status": 400,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": json.dumps(body).encode()})


class SessionAdmission:
    """Cap how many MCP sessions one client may hold open.

    The SDK's own limit is global, so without this one credential could open every
    session the gateway allows and lock out all other clients. Sessions are counted
    from the session ids the SDK hands out, and forgotten when the client deletes
    them or after the same idle timeout the SDK applies.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_sessions_per_client: int,
        idle_timeout_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._app = app
        self._max_sessions_per_client = max_sessions_per_client
        self._idle_timeout_s = idle_timeout_s
        self._clock = clock
        self._sessions: dict[str, _TrackedSession] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        user = scope.get("user") if scope["type"] == "http" else None
        if not isinstance(user, AuthenticatedUser):
            await self._app(scope, receive, send)
            return

        client_id = user.access_token.client_id
        session_id = Headers(scope=scope).get(_SESSION_ID_HEADER)
        now = self._clock()
        self._forget_idle(now)

        if session_id is None and self._open_sessions(client_id) >= self._max_sessions_per_client:
            await _send_json_rpc_error(
                send, 429, "Too many open sessions for this client. Close one and retry."
            )
            return

        status, issued_session_id = await _run_and_observe(self._app, scope, receive, send)
        if status is None or status >= 400:
            return
        if issued_session_id is not None and session_id is None:
            self._sessions[issued_session_id] = _TrackedSession(client_id, now)
        elif session_id is not None:
            self._touch_or_forget(session_id, client_id, scope["method"], now)

    def _open_sessions(self, client_id: str) -> int:
        return sum(1 for session in self._sessions.values() if session.client_id == client_id)

    def _forget_idle(self, now: float) -> None:
        idle = [
            session_id
            for session_id, session in self._sessions.items()
            if now - session.last_seen > self._idle_timeout_s
        ]
        for session_id in idle:
            del self._sessions[session_id]

    def _touch_or_forget(self, session_id: str, client_id: str, method: str, now: float) -> None:
        session = self._sessions.get(session_id)
        if session is None or session.client_id != client_id:
            return
        if method == "DELETE":
            del self._sessions[session_id]
        else:
            session.last_seen = now


@dataclass
class _TrackedSession:
    client_id: str
    last_seen: float


async def _run_and_observe(
    app: ASGIApp, scope: Scope, receive: Receive, send: Send
) -> tuple[int | None, str | None]:
    """Run the app; return the response status and any session id it issued."""
    status: int | None = None
    issued_session_id: str | None = None

    async def observe(message: Message) -> None:
        nonlocal status, issued_session_id
        if message["type"] == "http.response.start":
            status = message["status"]
            issued_session_id = Headers(raw=message.get("headers", [])).get(_SESSION_ID_HEADER)
        await send(message)

    await app(scope, receive, observe)
    return status, issued_session_id


async def _send_json_rpc_error(send: Send, status: int, message: str) -> None:
    body = {"jsonrpc": "2.0", "id": None, "error": {"code": INVALID_REQUEST, "message": message}}
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": json.dumps(body).encode()})


class SessionCleanup:
    """Close a session's upstream connections when its client ends the session.

    Only a DELETE the SDK accepted counts: the SDK answers 404 when the session id is
    unknown or belongs to another credential, and those must not close anything.
    """

    def __init__(self, app: ASGIApp, pool: UpstreamSessionPool) -> None:
        self._app = app
        self._pool = pool

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "DELETE":
            await self._app(scope, receive, send)
            return

        status: int | None = None

        async def capture_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        await self._app(scope, receive, capture_status)

        session_id = Headers(scope=scope).get(_SESSION_ID_HEADER)
        user = scope.get("user")
        if (
            session_id
            and isinstance(user, AuthenticatedUser)
            and status is not None
            and status < 400
        ):
            self._pool.close_session(session_id, UUID(user.access_token.client_id))
