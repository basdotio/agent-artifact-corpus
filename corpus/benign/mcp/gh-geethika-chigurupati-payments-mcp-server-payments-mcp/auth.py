"""JWT bearer-token verification with scope checks (HS256)."""
import time
from collections.abc import Mapping
from typing import Any

import jwt

ALGORITHM = "HS256"
ISSUER = "payments-mcp-server"
READ_SCOPE = "payments:read"
WRITE_SCOPE = "payments:write"


class AuthError(Exception):
    """Raised when a token is missing, invalid, expired, or lacks a required scope."""


def issue_token(secret: str, subject: str, scopes: list[str], ttl_seconds: int = 3600) -> str:
    """Create a signed token. Meant for local development and tests."""
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "sub": subject,
        "scope": " ".join(scopes),
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def verify_token(token: str, secret: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],  # never accept the algorithm named in the token header
            issuer=ISSUER,
            options={"require": ["exp", "sub", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("invalid token") from exc


def claims_from_headers(headers: Mapping[str, str], secret: str) -> dict[str, Any]:
    value = headers.get("authorization", "")
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthError("missing bearer token")
    return verify_token(token.strip(), secret)


def require_scope(claims: Mapping[str, Any], scope: str) -> None:
    granted = str(claims.get("scope", "")).split()
    if scope not in granted:
        raise AuthError(f"missing required scope: {scope}")
