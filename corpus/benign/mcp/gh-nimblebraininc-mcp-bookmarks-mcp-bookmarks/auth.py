"""Who is calling, and how the server knows.

A remote MCP server is an OAuth protected resource. It publishes where its tokens come
from (RFC 9728 protected resource metadata, served under `/.well-known/`), it answers an
unauthenticated call with 401 and a `WWW-Authenticate` header pointing at that document,
and it accepts a token only if the token was minted for this server: the `aud` claim has
to name the server's own URL, exactly. A token for the bare origin, for another server
on the same host, or for the client itself is refused with 401, and the client goes back
through discovery to get the right one.

Audience says where a token may be presented. It does not say what the caller may see.
That is the store's job: every row carries its owner, and a bookmark another owner holds
is answered exactly like one that does not exist.
"""

import logging
from pathlib import Path

from fastmcp.server.auth import AccessToken, JWTVerifier, RemoteAuthProvider
from fastmcp.server.dependencies import get_access_token
from pydantic import AnyHttpUrl

from .config import ANONYMOUS, Settings

logger = logging.getLogger("mcp_bookmarks.auth")


class SubjectRequired(JWTVerifier):
    """A token is someone's. One without a `sub` is refused at the door (401), because the
    verifier's `client_id` fallback would otherwise file every such token under one owner."""

    async def verify_token(self, token: str) -> AccessToken | None:
        verified = await super().verify_token(token)
        if verified is None or not verified.claims.get("sub"):
            return None
        return verified


def build_auth(settings: Settings) -> RemoteAuthProvider | None:
    """The auth provider for these settings, or None for an anonymous development server."""
    if not settings.auth_enabled:
        if not settings.allow_anonymous:
            raise RuntimeError(
                "No authentication configured. Set BOOKMARKS_PUBLIC_URL, BOOKMARKS_ISSUER, and "
                "BOOKMARKS_JWKS_URI (or BOOKMARKS_PUBLIC_KEY_FILE), or set "
                "BOOKMARKS_ALLOW_ANONYMOUS=true for local development."
            )
        logger.warning("BOOKMARKS_ALLOW_ANONYMOUS=true: every caller is %r", ANONYMOUS)
        return None
    if settings.public_url is None:
        raise RuntimeError(
            "BOOKMARKS_PUBLIC_URL is required when authentication is on: tokens are bound to it."
        )
    if settings.jwks_uri is None and settings.public_key_file is None:
        raise RuntimeError("Set BOOKMARKS_JWKS_URI or BOOKMARKS_PUBLIC_KEY_FILE.")
    public_key = Path(settings.public_key_file).read_text() if settings.public_key_file else None
    verifier = SubjectRequired(
        jwks_uri=settings.jwks_uri,
        public_key=public_key,
        issuer=settings.issuer,
        audience=settings.resource_url,
    )
    assert settings.issuer is not None
    return RemoteAuthProvider(
        token_verifier=verifier,
        authorization_servers=[AnyHttpUrl(settings.issuer)],
        base_url=settings.public_url,
        resource_name="Bookmarks",
    )


def current_owner() -> str:
    """The owner the current call acts as: the token's subject, or `anonymous` with auth off."""
    token = get_access_token()
    if token is None:
        return ANONYMOUS
    if not token.subject:
        # SubjectRequired refuses such a token before any tool runs.
        raise RuntimeError("an admitted token has no subject")
    return token.subject
