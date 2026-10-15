"""Runtime configuration, read from environment variables.

Every setting has a default that works against the public API with no setup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://clinicaltrials.gov/api/v2"
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_CACHE_TTL_SECONDS = 300.0
DEFAULT_MAX_RETRIES = 2


def _float_from_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_from_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Settings for the ClinicalTrials.gov client."""

    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            base_url=os.environ.get("CT_MCP_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            timeout_seconds=_float_from_env("CT_MCP_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
            cache_ttl_seconds=_float_from_env(
                "CT_MCP_CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS
            ),
            max_retries=max(0, _int_from_env("CT_MCP_MAX_RETRIES", DEFAULT_MAX_RETRIES)),
        )
