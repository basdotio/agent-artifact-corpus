"""Configuration management for template MCP server."""

from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable bindings."""

    model_config = SettingsConfigDict(
        env_prefix="TAXCODE_",
        env_file=".env",
        extra="ignore",
    )

    API_KEY: str = Field(default="", description="Service API token")
    BASE_URL: str = Field(default="https://api.example.com", description="Target REST API base URL")
    ALLOWED_HOSTS: str = Field(
        default="",
        description="Comma-separated hostname allowlist for SSRF defense",
    )
    TIMEOUT_SECONDS: float = Field(
        default=30.0,
        gt=0,
        description="HTTP request timeout in seconds",
    )
    MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts on HTTP 429 / 5xx",
    )
    DB_PATH: str = Field(
        default=":memory:",
        description="Path to DuckDB database file, or ':memory:' for transient storage",
    )

    # Safety Gating
    MCP_READONLY: bool = Field(
        default=False,
        description="Restrict server strictly to tools marked readOnlyHint=True",
    )
    MCP_ALLOW_BULK_DESTRUCTIVE: bool = Field(
        default=False,
        description="Gate required to register and execute batch destructive mutations",
    )

    # Transport Options (Spec 2026-07-28 / SEP-1049)
    MCP_STATELESS_HTTP: bool = Field(
        default=False,
        description="Enable stateless Streamable HTTP transport mode (Spec 2026-07-28 / SEP-1049)",
    )
    MCP_JSON_RESPONSE: bool = Field(
        default=False,
        description="Return direct application/json responses instead of SSE text/event-stream",
    )

    # Composition and Discovery
    MCP_ENABLE_TOOL_SEARCH: bool = Field(
        default=False,
        description=(
            "Opt-in Tool Search transform (search_tools + call_tool). "
            "Attached only when profile is 'full'."
        ),
    )
    MCP_TOOL_SEARCH_BACKEND: Literal["regex", "bm25"] = Field(
        default="regex",
        description="Tool Search backend: 'regex' (default) or 'bm25'",
    )
    MCP_ENABLE_CODE_MODE: bool = Field(
        default=False,
        description=(
            "Opt-in experimental Code Mode transform (search + execute). "
            "Attached only when profile is 'full'; mutually exclusive with Tool Search."
        ),
    )

    MCP_PROFILE: str = Field(
        default="full",
        description=(
            "Server profile: domain-mount profiles 'full', 'system', 'items', 'readonly', "
            "or a tool-name allowlist profile such as 'intake' (see profiles.PROFILES)"
        ),
    )

    @field_validator("MCP_TOOL_SEARCH_BACKEND", mode="before")
    @classmethod
    def _normalize_tool_search_backend(cls, value: Any) -> Any:
        """Accept ``BM25`` or `` bm25 `` from the env; unknown values still fail the Literal."""
        return value.strip().lower() if isinstance(value, str) else value


settings = Settings()
