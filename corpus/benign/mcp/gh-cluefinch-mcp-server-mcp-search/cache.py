"""In-memory TTL + LRU cache and conservative URL normalization.

A STDIO MCP server normally lives for one agent session, so persistent storage
would add complexity without providing meaningful benefits. This module keeps
the cache process-local and bounded.

Fetch results use a 10-minute TTL and search results use a 5-minute TTL.
Expired entries are removed lazily. When the cache reaches its size bound, the
least recently used entry is evicted.

URL normalization is intentionally conservative: query parameter ordering is
preserved because changing it could alter the semantics of some URLs.
Malformed URLs never raise from ``normalize_url``; they receive deterministic
opaque fallback keys instead.
"""

import math
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from mcp_search.config import (
    DEFAULT_CACHE_ENTRIES,
    DEFAULT_FETCH_TTL,
    DEFAULT_SEARCH_TTL,
    positive_float,
    positive_int,
)

if TYPE_CHECKING:
    from mcp_search.navigation import PageLink

FETCH_TTL = positive_float("FETCH_TTL", DEFAULT_FETCH_TTL)
SEARCH_TTL = positive_float("SEARCH_TTL", DEFAULT_SEARCH_TTL)
MAX_ENTRIES = positive_int("CACHE_ENTRIES", DEFAULT_CACHE_ENTRIES)


def _fallback_url_key(url: str) -> str:
    """Return a deterministic opaque key for a URL that cannot be normalized.

    The raw URL is deliberately not used as a cache key because malformed URLs
    may contain credentials or other unsafe data. Hashing preserves deterministic
    cache and deduplication behavior without propagating the original URL.
    """
    digest = sha256(url.encode("utf-8", errors="surrogatepass")).hexdigest()
    return f"unparsable:{digest}"


def normalize_url(url: str) -> str:
    """Return a conservative canonical cache key for a URL.

    The normalization:
    - lowercases the scheme and host;
    - removes a trailing dot from the host;
    - strips credentials;
    - removes fragments;
    - removes default HTTP/HTTPS ports;
    - preserves path and query parameter ordering;
    - formats IPv6 literals with brackets.

    Malformed URLs never raise. They receive deterministic opaque fallback keys.
    """
    try:
        parts = urlsplit(url, scheme="")
    except ValueError:
        return _fallback_url_key(url)

    scheme = parts.scheme
    path = parts.path
    query = parts.query

    if (
        not isinstance(scheme, str)
        or not isinstance(path, str)
        or not isinstance(query, str)
    ):
        return _fallback_url_key(url)

    scheme = scheme.lower()

    try:
        host = (parts.hostname or "").lower().rstrip(".")
        port = parts.port
    except ValueError:
        return _fallback_url_key(url)

    if not host:
        return _fallback_url_key(url)

    host_part = f"[{host}]" if ":" in host else host
    netloc = host_part
    if port is not None:
        if (scheme, port) not in (("http", 80), ("https", 443)):
            netloc = f"{host_part}:{port}"

    components: tuple[str, str, str, str, str] = (
        scheme,
        netloc,
        path or "/",
        query,
        "",
    )
    return urlunsplit(components)


class TTLCache[K: Hashable, V]:
    """Bounded in-memory TTL + LRU cache.

    ``clock`` is injectable so expiration behavior can be tested without
    monkeypatching or real sleeps.

    Expired entries are removed lazily on access. The size bound may evict
    entries before their TTL expires, which is intentional LRU behavior.
    Updating an existing key never evicts another entry.
    """

    def __init__(
        self,
        *,
        default_ttl: float,
        max_entries: int = MAX_ENTRIES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not math.isfinite(default_ttl) or default_ttl <= 0:
            raise ValueError("default_ttl must be positive")
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")

        self._data: OrderedDict[K, tuple[float, V]] = OrderedDict()
        self._default_ttl = default_ttl
        self._max_entries = max_entries
        self._clock = clock

    def get(self, key: K) -> V | None:
        """Return a non-expired value and mark its key as recently used."""
        entry = self._data.get(key)
        if entry is None:
            return None

        expires_at, value = entry

        if self._clock() >= expires_at:
            del self._data[key]
            return None

        self._data.move_to_end(key)
        return value

    def set(self, key: K, value: V, ttl: float | None = None) -> None:
        """Store a value using the default TTL unless an override is provided."""
        effective_ttl = self._default_ttl if ttl is None else ttl

        if not math.isfinite(effective_ttl) or effective_ttl <= 0:
            raise ValueError("ttl must be positive")

        if key in self._data:
            self._data.move_to_end(key)
        elif len(self._data) >= self._max_entries:
            self._data.popitem(last=False)

        self._data[key] = (self._clock() + effective_ttl, value)

    def clear(self) -> None:
        """Remove all cached entries."""
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


@dataclass(frozen=True, slots=True, kw_only=True)
class CachedPage:
    """Retained page data shared by cache aliases, without per-call cache status."""

    url: str
    title: str
    text: str
    text_truncated: bool
    links: tuple["PageLink", ...]
    links_truncated: bool
    text_sufficient: bool


fetch_cache = TTLCache[str, CachedPage](default_ttl=FETCH_TTL)

search_cache = TTLCache[tuple[Hashable, ...], dict[str, object]](default_ttl=SEARCH_TTL)
