"""Settings, from the environment and nowhere else.

A client never gets to choose where the data lives or who the server trusts. In
particular the server's own public URL is configuration, not something read off the
request's Host header, because that URL is what tokens are bound to.
"""

import os
from dataclasses import dataclass

MCP_PATH = "/mcp"
ANONYMOUS = "anonymous"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    db_path: str = "bookmarks.db"
    public_url: str | None = None
    """Where clients reach this server, scheme and host, no path: https://bookmarks.example.com"""
    issuer: str | None = None
    """The authorization server, exactly as it prints its `iss` claim."""
    jwks_uri: str | None = None
    """Where the issuer publishes its signing keys."""
    public_key_file: str | None = None
    """A PEM public key instead of a JWKS, for development."""
    allow_anonymous: bool = False
    """Run with no authentication; every caller is the same owner. Development only."""

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ.get
        return cls(
            db_path=env("BOOKMARKS_DB", "bookmarks.db"),
            public_url=env("BOOKMARKS_PUBLIC_URL") or None,
            issuer=env("BOOKMARKS_ISSUER") or None,
            jwks_uri=env("BOOKMARKS_JWKS_URI") or None,
            public_key_file=env("BOOKMARKS_PUBLIC_KEY_FILE") or None,
            allow_anonymous=_truthy(env("BOOKMARKS_ALLOW_ANONYMOUS")),
        )

    @property
    def auth_enabled(self) -> bool:
        return self.issuer is not None

    @property
    def resource_url(self) -> str:
        """The canonical URL of this MCP server: the string every token's `aud` must name."""
        if self.public_url is None:
            raise RuntimeError("BOOKMARKS_PUBLIC_URL is not set")
        return self.public_url.rstrip("/") + MCP_PATH
