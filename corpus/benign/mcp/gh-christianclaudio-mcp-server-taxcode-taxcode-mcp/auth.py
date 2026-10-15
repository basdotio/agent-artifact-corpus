"""Bearer token authentication and the bind policy for the HTTP transports.

``TAXCODE_MCP_AUTH_TOKEN`` is enforced through FastMCP's built-in server auth: a
``TokenVerifier`` subclass set as the server's ``auth`` provider
(https://gofastmcp.com/servers/auth/token-verification). FastMCP applies server auth
only to HTTP transports; stdio is unaffected
(https://gofastmcp.com/servers/auth/authentication).

The MCP spec says a local server SHOULD bind only to localhost and SHOULD authenticate
every connection
(https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http).
FastMCP servers default to ``auth=None``, so ``create_server`` attaches the verifier at build
whenever the token is set, covering ``fastmcp run`` and ``http_app()`` too.
``main()`` also refuses an HTTP bind to any other host unless a token is set or
``TAXCODE_MCP_ALLOW_UNAUTHENTICATED_BIND`` opts in.
"""

from __future__ import annotations

import hmac
import os

from fastmcp.server.auth import AccessToken, TokenVerifier

AUTH_TOKEN_ENV = "TAXCODE_MCP_AUTH_TOKEN"
ALLOW_UNAUTHENTICATED_BIND_ENV = "TAXCODE_MCP_ALLOW_UNAUTHENTICATED_BIND"
LOCALHOST_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
_TRUTHY = frozenset({"1", "true", "yes", "on"})


class SharedTokenVerifier(TokenVerifier):
    """Accept exactly one shared bearer token, compared in constant time."""

    def __init__(self, expected_token: str) -> None:
        stripped = expected_token.strip()
        if not stripped:
            raise ValueError(f"{AUTH_TOKEN_ENV} must be non-empty to enable authentication")
        super().__init__()
        self._expected = stripped.encode("utf-8")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(expected_token=***REDACTED***)"

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return an access token when ``token`` matches, else ``None`` (FastMCP answers 401)."""
        if not token.strip():
            return None
        if not hmac.compare_digest(token.encode("utf-8"), self._expected):
            return None
        return AccessToken(token=token, client_id="taxcode-mcp-shared-token", scopes=[])


def read_auth_token() -> str:
    """Return the stripped ``TAXCODE_MCP_AUTH_TOKEN``; whitespace-only counts as unset (``""``)."""
    return os.environ.get(AUTH_TOKEN_ENV, "").strip()


def allow_unauthenticated_bind() -> bool:
    """True when ``TAXCODE_MCP_ALLOW_UNAUTHENTICATED_BIND`` is 1/true/yes/on (any case)."""
    return os.environ.get(ALLOW_UNAUTHENTICATED_BIND_ENV, "").strip().lower() in _TRUTHY


def is_localhost(host: str) -> bool:
    """True for the loopback bind names 127.0.0.1, ::1 (bracketed or not), and localhost."""
    return host.strip().strip("[]").lower() in LOCALHOST_HOSTS
