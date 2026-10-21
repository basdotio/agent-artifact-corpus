"""Loopback-only authenticated TEST transport around the released MCP HTTP app.

The fixed bearer strings are public test fixtures. The outer ASGI wrapper is
trusted to establish identity before SDK dispatch. It is not an IdP.
"""

from __future__ import annotations

import contextvars
import os
from collections.abc import Awaitable, Callable

import uvicorn
from starlette.responses import PlainTextResponse
from starlette.types import Receive, Scope, Send

from reference.backend import IssueStore
from reference.guarded_server_stdio import _FrozenTime, build_server, load_settings

_TEST_TOKENS = {"Bearer test-alice-v1": "alice", "Bearer test-bob-v1": "bob"}
_principal: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "test_principal", default=None
)


def test_principal() -> str:
    value = _principal.get()
    if value is None:
        raise PermissionError("test principal missing")
    return value


class TestAuth:
    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = [(key.lower(), value) for key, value in scope.get("headers", [])]
        authorization = [
            value.decode("ascii", errors="replace")
            for key, value in headers
            if key == b"authorization"
        ]
        principal = _TEST_TOKENS.get(authorization[0]) if len(authorization) == 1 else None
        if principal is None:
            await PlainTextResponse("test authentication required", status_code=401)(
                scope, receive, send
            )
            return
        token = _principal.set(principal)
        try:
            await self.app(scope, receive, send)
        finally:
            _principal.reset(token)


def main() -> None:
    settings = load_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    _FrozenTime.value = settings.now_epoch
    import mcp.server.request_state as request_state_module

    request_state_module.time = _FrozenTime  # type: ignore[assignment]
    store = IssueStore(str(settings.db_path), backend_id=settings.backend_id)
    app = build_server(store, settings, principal_for_request=test_principal).streamable_http_app(
        json_response=True, stateless_http=True, host="127.0.0.1"
    )
    port = int(os.environ.get("WIRE_HTTP_PORT", "0"))
    if not 1 <= port <= 65535:
        raise SystemExit("WIRE_HTTP_PORT must be an assigned loopback port")
    uvicorn.run(TestAuth(app), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
