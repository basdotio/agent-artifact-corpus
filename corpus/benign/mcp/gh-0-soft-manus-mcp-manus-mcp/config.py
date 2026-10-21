"""Runtime configuration loaded from environment and .env file."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_webhook_db_path() -> Path:
    """Platform-specific default for webhook event storage."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "manus-mcp" / "events.db"


class Settings(BaseSettings):
    """Process configuration. process.env wins over .env (pydantic-settings default)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    manus_api_key: str = Field(
        ...,
        validation_alias=AliasChoices("MANUS_API_KEY", "ManusAPI", "manus_api_key"),
        description="Manus API key — see https://manus.im/app/settings/api",
    )
    manus_base_url: str = Field(
        default="https://api.manus.ai",
        validation_alias=AliasChoices("MANUS_BASE_URL", "manus_base_url"),
    )
    manus_http_timeout: float = Field(
        default=60.0,
        validation_alias=AliasChoices("MANUS_HTTP_TIMEOUT", "manus_http_timeout"),
        ge=1.0,
        le=600.0,
    )
    manus_log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("MANUS_LOG_LEVEL", "manus_log_level"),
    )

    manus_webhook_public_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MANUS_WEBHOOK_PUBLIC_URL", "manus_webhook_public_url"),
    )
    manus_webhook_db_path: Path = Field(
        default_factory=_default_webhook_db_path,
        validation_alias=AliasChoices("MANUS_WEBHOOK_DB_PATH", "manus_webhook_db_path"),
    )
    manus_webhook_host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("MANUS_WEBHOOK_HOST", "manus_webhook_host"),
    )
    manus_webhook_port: int = Field(
        default=8787,
        validation_alias=AliasChoices("MANUS_WEBHOOK_PORT", "manus_webhook_port"),
        ge=1,
        le=65535,
    )

    @field_validator("manus_base_url")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("manus_log_level")
    @classmethod
    def _normalize_log_level(cls, v: str) -> str:
        upper = v.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if upper not in allowed:
            raise ValueError(f"manus_log_level must be one of {allowed}, got {v!r}")
        return upper


def load_settings() -> Settings:
    """Load settings. Raises pydantic.ValidationError if MANUS_API_KEY is missing."""
    return Settings()
