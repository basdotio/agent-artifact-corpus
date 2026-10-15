"""Configuration for the proxy using Pydantic Settings.

Follows modern Python practices and keeps configuration isolated (SRP).
"""

from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class ProxySettings(BaseSettings):
    """Application settings loaded from environment or .env.

    The backend (the MCP server this proxy fronts) can be configured two ways:

    - **JSON config file** (`backend_config`): a path to a standard ``mcpServers``
      config file (the same format Claude Desktop / Cursor / Copilot use). Takes
      precedence when set. Parsed and validated by FastMCP's ``MCPConfig``.
    - **Individual fields** (`backend_mcp_url` + `backend_api_key`): the direct
      env-var route. `backend_api_key` is required in this mode.

    All sensitive values (API keys / tokens) must come from the environment, the
    ``.env`` file, or the backend config file - never hard-coded.
    """

    # Backend selection: a standard mcpServers JSON config file. When set, it
    # takes precedence over the individual backend_* fields below and supplies
    # the URL/transport/auth itself. TLS verification is still governed by
    # `backend_verify_tls` (the mcpServers format has no verify field).
    backend_config: str | None = Field(
        default=None,
        description="Path to a standard mcpServers JSON config file describing the "
        "single backend MCP server. Takes precedence over backend_mcp_url/"
        "backend_api_key when set.",
    )

    # Upstream backend MCP - the individual-field route,
    # used when `backend_config` is not set.
    backend_mcp_url: str = Field(
        default="https://127.0.0.1:12345/mcp/",
        description="Full URL to the backend's Streamable HTTP MCP endpoint.",
    )
    backend_api_key: str | None = Field(
        default=None,
        description="Bearer token for the backend's authentication. Required "
        "unless backend_config is set.",
    )
    backend_verify_tls: bool = Field(
        default=False,
        description="Whether to verify the backend's TLS certificate. False for self-signed certs.",
    )

    # Our exposed (listen) server
    server_name: str = Field(
        default="mcp-call-orchestrator-proxy",
        description="Name the proxy reports as its MCP server identity (the "
        "`initialize` handshake's server name). Distinct clients dedupe/label "
        "servers by this, not by whatever key you gave it in your own MCP "
        "client config - set a unique value per backend when running more "
        "than one instance, or every instance looks identical to clients "
        "like VS Code/Copilot.",
    )
    listen_host: str = Field(
        default="127.0.0.1", description="Host the proxy MCP server binds to."
    )
    listen_port: int = Field(
        default=27125,
        description="Port the proxy MCP server listens on.",
        ge=1,
        le=65535,
    )

    # Orchestration
    max_concurrent_calls: int = Field(
        default=1,
        description="Maximum concurrent calls to the backend (1 = fully serialized).",
        ge=1,
    )
    call_timeout_seconds: float = Field(
        default=120.0,
        description="Timeout for a single backend tool call.",
        gt=0,
    )

    # Resilience: connecting to a backend that comes and goes
    connect_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout for a single backend connect/initialize attempt.",
        gt=0,
    )
    reconnect_initial_backoff_seconds: float = Field(
        default=1.0,
        description="First delay before retrying a failed backend connection.",
        gt=0,
    )
    reconnect_max_backoff_seconds: float = Field(
        default=30.0,
        description="Cap on the exponential reconnect backoff delay.",
        gt=0,
    )
    reconnect_backoff_multiplier: float = Field(
        default=2.0,
        description="Factor the reconnect backoff grows by after each failure.",
        ge=1.0,
    )
    backend_health_poll_seconds: float = Field(
        default=5.0,
        description="How often the supervisor re-checks a held connection (local, "
        "no network traffic to the backend).",
        gt=0,
    )

    # Observability
    log_level: LogLevel = Field(
        default="INFO",
        description="Logging verbosity. INFO shows the queue working (a record per "
        "call on acceptance and on completion); DEBUG adds the internal detail for "
        "fault-finding; WARNING and above shows only what needs an operator.",
    )

    # Exposure control: per-surface allow/deny name lists (exact match).
    # Blank / absent = unset (not "allow nothing"). See exposure.py.
    tool_allow: tuple[str, ...] | None = Field(
        default=None,
        description="Comma-separated tool names to allow (exact match). When set, "
        "only these tools are exposed; any tool deny-list is ignored.",
    )
    tool_deny: tuple[str, ...] | None = Field(
        default=None,
        description="Comma-separated tool names to hide (exact match). Ignored "
        "when tool_allow is also set.",
    )
    resource_allow: tuple[str, ...] | None = Field(
        default=None,
        description="Comma-separated resource URIs / template uriTemplates to "
        "allow (exact match). When set, only these are exposed; resource_deny is "
        "ignored.",
    )
    resource_deny: tuple[str, ...] | None = Field(
        default=None,
        description="Comma-separated resource URIs / template uriTemplates to "
        "hide (exact match). Ignored when resource_allow is also set.",
    )
    prompt_allow: tuple[str, ...] | None = Field(
        default=None,
        description="Comma-separated prompt names to allow (exact match). When "
        "set, only these prompts are exposed; prompt_deny is ignored.",
    )
    prompt_deny: tuple[str, ...] | None = Field(
        default=None,
        description="Comma-separated prompt names to hide (exact match). Ignored "
        "when prompt_allow is also set.",
    )

    model_config = SettingsConfigDict(
        env_prefix="MCP_PROXY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: Any) -> Any:
        """Accept `debug` as readily as `DEBUG`, but still reject a typo.

        A silently-ignored `--log-level VERBOSE` is the worst possible failure for
        the one switch whose entire job is turning on detail you are about to go
        looking for. Normalizing case here keeps the `Literal` free to reject
        everything else.
        """
        return value.upper() if isinstance(value, str) else value

    @field_validator(
        "tool_allow",
        "tool_deny",
        "resource_allow",
        "resource_deny",
        "prompt_allow",
        "prompt_deny",
        mode="before",
    )
    @classmethod
    def _parse_name_list(cls, value: Any) -> tuple[str, ...] | None:
        """Split a comma-separated name list; blank → unset (None).

        Empty string and whitespace-only / empty segments never become an empty
        allow-list ("expose nothing") — that would lock clients out from a
        blank shell template. Names are not case-folded.
        """
        if value is None:
            return None
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",")]
        elif isinstance(value, (list, tuple)):
            parts = [str(part).strip() for part in value]
        else:
            # Leave non-string/sequence values for pydantic to reject.
            msg = f"name list must be a string or sequence, got {type(value).__name__}"
            raise TypeError(msg)

        # Preserve first-seen order; drop blanks and duplicates.
        names = tuple(dict.fromkeys(p for p in parts if p))
        return names or None

    @model_validator(mode="after")
    def _require_a_backend_source(self) -> "ProxySettings":
        """Ensure a backend is actually configured.

        A JSON config file (`backend_config`) supplies its own auth, so the
        individual `backend_api_key` is optional in that mode. Without a config
        file we fall back to the individual fields, where a bearer token is
        required to authenticate against the backend.
        """
        if self.backend_config is None and not self.backend_api_key:
            raise ValueError(
                "No backend configured: set MCP_PROXY_BACKEND_CONFIG (path to an "
                "mcpServers JSON file) or MCP_PROXY_BACKEND_API_KEY (with "
                "MCP_PROXY_BACKEND_MCP_URL)."
            )
        return self


def get_settings(**overrides: Any) -> ProxySettings:
    """Factory for settings. Enables easy overriding in tests (DIP)."""
    if overrides:
        return ProxySettings(**overrides)
    return ProxySettings()
