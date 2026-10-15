"""Runtime configuration for the Plane MCP server.

All values are read from environment variables so the server can be launched
directly by an MCP client over stdio or deployed behind an HTTP transport.

    PLANE_API_KEY         Personal access token (``X-API-Key`` header).
                          Alias: PLANE_TOKEN.
    PLANE_OAUTH_TOKEN     Alternative OAuth bearer token.
    PLANE_WORKSPACE_SLUG  Target workspace slug (from the app URL).
                          Alias: PLANE_WORKSPACE.
    PLANE_BASE_URL        Plane instance URL; defaults to https://api.plane.so.
                          Alias: PLANE_URL.
                          Self-hosted examples:
                            https://plane.example.com
                            https://example.com/plane        (subpath install)
                            https://plane.example.com/api/v1 (already versioned)
    PLANE_TIMEOUT         Request timeout in seconds (default 30).

Values may also be provided with ``plane-mcp --base-url ... --workspace ...``;
CLI flags win over the process environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.plane.so"


class ConfigError(RuntimeError):
    """Raised when required Plane credentials are missing or invalid."""


def normalize_base_url(value: str) -> str:
    """Return the API root, including the ``/api/v1`` suffix.

    Handles the shapes people actually paste for a self-hosted instance:
    a bare host, a host with a subpath, a trailing slash, or a URL that
    already ends in ``/api/v1``.
    """
    url = (value or DEFAULT_BASE_URL).strip().rstrip("/")
    if not url:
        url = DEFAULT_BASE_URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if url.endswith("/api/v1"):
        return url
    return url + "/api/v1"


def _first(source: dict[str, str], *names: str) -> str | None:
    """Return the first non-empty value among ``names``."""
    for name in names:
        value = (source.get(name) or "").strip()
        if value:
            return value
    return None



@dataclass(frozen=True)
class Settings:
    """Resolved server settings."""

    workspace_slug: str
    base_url: str
    api_key: str | None = None
    oauth_token: str | None = None
    timeout: float = 30.0

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        source = os.environ if env is None else env

        api_key = _first(source, "PLANE_API_KEY", "PLANE_TOKEN")
        oauth_token = _first(source, "PLANE_OAUTH_TOKEN")
        workspace_slug = _first(source, "PLANE_WORKSPACE_SLUG", "PLANE_WORKSPACE") or ""
        base_url = normalize_base_url(_first(source, "PLANE_BASE_URL", "PLANE_URL") or DEFAULT_BASE_URL)

        raw_timeout = (source.get("PLANE_TIMEOUT") or "30").strip()
        try:
            timeout = float(raw_timeout)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ConfigError(f"PLANE_TIMEOUT must be a number, got {raw_timeout!r}") from exc

        return cls(
            workspace_slug=workspace_slug,
            base_url=base_url,
            api_key=api_key,
            oauth_token=oauth_token,
            timeout=timeout,
        )

    def validate(self) -> "Settings":
        """Raise :class:`ConfigError` if the settings cannot authenticate."""
        if not self.api_key and not self.oauth_token:
            raise ConfigError(
                "No Plane credentials found. Set PLANE_API_KEY (recommended) or "
                "PLANE_OAUTH_TOKEN. Create a personal access token in Plane under "
                "Profile settings -> Personal access tokens."
            )
        if not self.workspace_slug:
            raise ConfigError(
                "PLANE_WORKSPACE_SLUG is not set. It is the slug in your Plane URL, "
                "for example 'my-team' in https://app.plane.so/my-team/projects/ "
                "(for a self-hosted instance the slug is the first path segment)."
            )
        return self

    def redacted(self) -> dict[str, object]:
        """A log-safe view of the resolved configuration (no secrets)."""
        return {
            "base_url": self.base_url,
            "workspace_slug": self.workspace_slug,
            "auth": "api_key" if self.api_key else ("oauth_token" if self.oauth_token else "none"),
            "timeout": self.timeout,
        }
