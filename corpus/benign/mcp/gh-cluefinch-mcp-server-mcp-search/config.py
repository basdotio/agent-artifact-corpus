"""Validated deployment settings and canonical runtime defaults."""

import math
import os
from types import MappingProxyType
from typing import Final

DEFAULT_SEARXNG_URL: Final = "http://127.0.0.1:8081"
DEFAULT_ENGINES: Final[tuple[str, ...]] = (
    "google",
    "google cse",
    "brave",
    "wikipedia",
    "wikidata",
)
DEFAULT_MAX_RESULTS: Final = 20
DEFAULT_MAX_FETCH_CHARS: Final = 20_000
DEFAULT_MAX_SOURCES: Final = 10
DEFAULT_MAX_QUERIES: Final = 10
DEFAULT_EXPAND_CHARS: Final = 3000
DEFAULT_SEARCH_INTERVAL: Final = 5.0
DEFAULT_FETCH_TTL: Final = 600.0
DEFAULT_SEARCH_TTL: Final = 300.0
DEFAULT_CACHE_ENTRIES: Final = 500
DEFAULT_MAX_REDIRECTS: Final = 5
DEFAULT_MAX_RESPONSE_BYTES: Final = 5 * 1024 * 1024
DEFAULT_MAX_TEXT_CHARS: Final = 100_000
DEFAULT_DOWNLOAD_TIMEOUT: Final = 60.0
DEFAULT_EXTRACT_CONCURRENCY: Final = 2
DEFAULT_MIN_EXTRACTED_CHARS: Final = 100
DEFAULT_FETCH_CONCURRENCY: Final = 3
DEFAULT_HOST_INTERVAL: Final = 5.0

RUNTIME_DEFAULTS = MappingProxyType(
    {
        "SEARXNG_URL": DEFAULT_SEARXNG_URL,
        "ENGINES": DEFAULT_ENGINES,
        "MAX_RESULTS": DEFAULT_MAX_RESULTS,
        "MAX_FETCH_CHARS": DEFAULT_MAX_FETCH_CHARS,
        "MAX_SOURCES": DEFAULT_MAX_SOURCES,
        "MAX_QUERIES": DEFAULT_MAX_QUERIES,
        "EXPAND_CHARS": DEFAULT_EXPAND_CHARS,
        "SEARCH_INTERVAL": DEFAULT_SEARCH_INTERVAL,
        "FETCH_TTL": DEFAULT_FETCH_TTL,
        "SEARCH_TTL": DEFAULT_SEARCH_TTL,
        "CACHE_ENTRIES": DEFAULT_CACHE_ENTRIES,
        "MAX_REDIRECTS": DEFAULT_MAX_REDIRECTS,
        "MAX_RESPONSE_BYTES": DEFAULT_MAX_RESPONSE_BYTES,
        "MAX_TEXT_CHARS": DEFAULT_MAX_TEXT_CHARS,
        "DOWNLOAD_TIMEOUT": DEFAULT_DOWNLOAD_TIMEOUT,
        "EXTRACT_CONCURRENCY": DEFAULT_EXTRACT_CONCURRENCY,
        "MIN_EXTRACTED_CHARS": DEFAULT_MIN_EXTRACTED_CHARS,
        "FETCH_CONCURRENCY": DEFAULT_FETCH_CONCURRENCY,
        "HOST_INTERVAL": DEFAULT_HOST_INTERVAL,
    }
)


def positive_int(name: str, default: int) -> int:
    raw = os.environ.get(f"MCP_SEARCH_{name}", str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"MCP_SEARCH_{name} must be a positive integer") from exc
    if value < 1:
        raise ValueError(f"MCP_SEARCH_{name} must be a positive integer")
    return value


def positive_float(name: str, default: float) -> float:
    raw = os.environ.get(f"MCP_SEARCH_{name}", str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"MCP_SEARCH_{name} must be a positive number") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"MCP_SEARCH_{name} must be a positive number")
    return value
