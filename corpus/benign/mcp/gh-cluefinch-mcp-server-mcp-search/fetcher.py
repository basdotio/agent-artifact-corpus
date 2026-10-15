"""HTTP fetching with SSRF-safe validation, manual redirects, size caps, extraction.

Pipeline: validate URL (security.validate_url) -> cache lookup -> streamed GET
with re-validation at every redirect hop (max 5) -> Content-Length pre-check +
5 MB streaming cap post-decompression (decompression-bomb guard) -> content-type
guard -> bounded text and link extraction. Text uses Trafilatura Markdown with
a stripped-BS4 fallback; navigation retains a separately bounded <a href> view.

Validation happens BEFORE the cache lookup in fetch_page: canonical keys
collapse URL variants (credentials, trailing dots, default ports), so a cache
hit must never bypass the security contract.

HTTP client: a single lazily-created AsyncClient is shared by all fetches —
connection reuse matters for research_collect's concurrent fetches. The
process must close it at shutdown via close_http_client() (called from
server.py).

Environment proxy inheritance is disabled deliberately. SSRF validation is
performed by this process against the destination it intends to contact; an
HTTP(S) proxy would move DNS resolution and the actual target connection to a
different transport boundary.

JavaScript rendering is deliberately not performed in v1. Browser request
routing does not provide a complete per-redirect SSRF boundary: redirected
top-level or subresource requests can leave the route handler after the first
validated URL. A safe browser fallback requires a controlled outbound proxy,
pinned transport, or equivalent network sandbox. Low-text HTML remains a valid
shared page result so link navigation can still use it; reading/collection layers
report insufficient readable text without discarding its navigation data.

stdout is the MCP protocol: no print() anywhere in this package.
"""

import asyncio
import os
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Final
from urllib.parse import urljoin

import httpx
import trafilatura
from bs4 import BeautifulSoup, UnicodeDammit

from mcp_search import __version__
from mcp_search.cache import CachedPage, fetch_cache, normalize_url
from mcp_search.config import (
    DEFAULT_DOWNLOAD_TIMEOUT,
    DEFAULT_EXTRACT_CONCURRENCY,
    DEFAULT_FETCH_CONCURRENCY,
    DEFAULT_HOST_INTERVAL,
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_MAX_TEXT_CHARS,
    DEFAULT_MIN_EXTRACTED_CHARS,
    positive_float,
    positive_int,
)
from mcp_search.limits import RequestLimiter
from mcp_search.metadata_limits import MAX_TITLE_CHARS, truncate_metadata
from mcp_search.navigation import NavigationResult, PageLink, extract_navigation
from mcp_search.security import SecurityError, validate_url
from mcp_search.transport import SafeTransport
from mcp_search.url_limits import MAX_URL_CHARS, exceeds_url_limit

MAX_REDIRECTS: Final = positive_int("MAX_REDIRECTS", DEFAULT_MAX_REDIRECTS)
MAX_RESPONSE_BYTES: Final = positive_int(
    "MAX_RESPONSE_BYTES", DEFAULT_MAX_RESPONSE_BYTES
)
MAX_TEXT_CHARS: Final = positive_int("MAX_TEXT_CHARS", DEFAULT_MAX_TEXT_CHARS)
DOWNLOAD_TIMEOUT: Final = positive_float("DOWNLOAD_TIMEOUT", DEFAULT_DOWNLOAD_TIMEOUT)
EXTRACT_CONCURRENCY: Final = positive_int(
    "EXTRACT_CONCURRENCY", DEFAULT_EXTRACT_CONCURRENCY
)

# A configurable extraction-failure heuristic, not a security boundary.
MIN_EXTRACTED_CHARS: Final = positive_int(
    "MIN_EXTRACTED_CHARS", DEFAULT_MIN_EXTRACTED_CHARS
)

# Deployments can override this through MCP_SEARCH_UA.
DEFAULT_UA: Final = (
    f"Cluefinch/{__version__} (+https://github.com/cluefinch/mcp-server)"
)

ALLOWED_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {"text/html", "application/xhtml+xml"}
)

REDIRECT_STATUSES: Final[frozenset[int]] = frozenset({301, 302, 303, 307, 308})

HTTP_TIMEOUT: Final = httpx.Timeout(connect=5, read=15, write=10, pool=5)


@dataclass(frozen=True, slots=True)
class FetchResult:
    """Extracted result returned by fetch_page."""

    url: str  # final URL after redirects
    title: str
    text: str  # full extracted markdown (capped at MAX_TEXT_CHARS)
    cache_hit: bool = False
    text_truncated: bool = False
    links: tuple[PageLink, ...] = ()
    links_truncated: bool = False
    text_sufficient: bool = True  # Suitability of extraction before retention limits.


class FetchError(Exception):
    """Expected fetch failure with message, hint, and machine kind.

    ``kind`` lets tool-layer code branch without string matching
    (e.g. ``kind="timeout"`` identifies a download timeout).
    """

    def __init__(self, error: str, hint: str = "", *, kind: str = "") -> None:
        super().__init__(error)
        self.error = error
        self.hint = hint
        self.kind = kind


_client: httpx.AsyncClient | None = None
_limiter: RequestLimiter | None = None
_extract_executor: ThreadPoolExecutor | None = None
_extract_slots: asyncio.Semaphore | None = None
_fetch_flights: dict[str, asyncio.Task[FetchResult]] = {}
_close_task: asyncio.Task[None] | None = None
_resource_generation = 0


def _ensure_open() -> None:
    """Prevent new work from acquiring shared resources during teardown."""
    if _close_task is not None:
        raise FetchError("fetch resources are shutting down", kind="shutdown")


def _user_agent() -> str:
    """Return the configured UA.

    The environment is read each time this helper is called. The shared HTTP
    client snapshots the resulting value when the client is created; tests
    changing MCP_SEARCH_UA after that must call close_http_client() first.
    """
    return os.environ.get("MCP_SEARCH_UA", DEFAULT_UA).strip() or DEFAULT_UA


def _get_client() -> httpx.AsyncClient:
    """Return the shared keep-alive/pooling HTTP client."""
    global _client

    _ensure_open()
    client = _client
    if client is None or client.is_closed:
        client = httpx.AsyncClient(
            transport=SafeTransport(),
            follow_redirects=False,
            timeout=HTTP_TIMEOUT,
            trust_env=False,
            headers={
                "Accept-Encoding": "gzip, identity",
                "User-Agent": _user_agent(),
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
            },
        )
        _client = client

    return client


def _get_limiter() -> RequestLimiter:
    global _limiter
    _ensure_open()
    limiter = _limiter
    if limiter is None:
        limiter = RequestLimiter(
            concurrency=positive_int("FETCH_CONCURRENCY", DEFAULT_FETCH_CONCURRENCY),
            interval=positive_float("HOST_INTERVAL", DEFAULT_HOST_INTERVAL),
        )
        _limiter = limiter
    return limiter


def _get_extract_executor() -> ThreadPoolExecutor:
    """Return the dedicated bounded parser pool.

    Extraction does not use asyncio's default executor so parser CPU work cannot
    consume workers also used by DNS resolution and unrelated to_thread calls.
    """
    global _extract_executor
    _ensure_open()
    executor = _extract_executor
    if executor is None:
        executor = ThreadPoolExecutor(
            max_workers=EXTRACT_CONCURRENCY, thread_name_prefix="cluefinch-extract"
        )
        _extract_executor = executor
    return executor


def _get_extract_slots() -> asyncio.Semaphore:
    """Bound submitted extraction work, including callers canceled mid-parse."""
    global _extract_slots
    _ensure_open()
    slots = _extract_slots
    if slots is None:
        slots = asyncio.Semaphore(EXTRACT_CONCURRENCY)
        _extract_slots = slots
    return slots


async def _extract_bounded(
    html: str, base_url: str
) -> tuple[str, str, NavigationResult]:
    """Run extraction in the dedicated pool under a real-worker completion slot.

    Cancellation of the awaiting coroutine does not release the slot while the
    underlying parser thread is still running. Threads cannot be force-killed; a
    hard execution boundary would require process isolation.
    """
    generation = _resource_generation
    slots = _get_extract_slots()
    await slots.acquire()
    loop = asyncio.get_running_loop()

    try:
        if generation != _resource_generation:
            raise FetchError("extraction interrupted by shutdown", kind="shutdown")
        worker = _get_extract_executor().submit(_extract, html, base_url)
    except BaseException:
        slots.release()
        raise

    def release_slot(_future: object) -> None:
        try:
            loop.call_soon_threadsafe(slots.release)
        except RuntimeError:
            # The event loop may already be closed during process teardown.
            pass

    worker.add_done_callback(release_slot)
    return await asyncio.wrap_future(worker)


async def _close_resources() -> None:
    """Drain fetch tasks before closing their resources, even on close failure."""
    global _client, _limiter, _extract_executor, _extract_slots, _close_task
    client = _client
    executor = _extract_executor
    flights = list(_fetch_flights.values())
    try:
        try:
            for task in flights:
                task.cancel()
            await asyncio.gather(*flights, return_exceptions=True)
        finally:
            try:
                if client is not None and not client.is_closed:
                    await client.aclose()
            finally:
                if executor is not None:
                    executor.shutdown(wait=False, cancel_futures=True)
    finally:
        _fetch_flights.clear()
        _client = None
        _limiter = None
        _extract_executor = None
        _extract_slots = None
        _close_task = None


async def close_http_client() -> None:
    """Drain fetch tasks and close shared resources in a single shutdown operation.

    Concurrent callers share cleanup; cancelling a caller does not cancel it.
    New work is rejected during teardown. After completion, a new call can lazily
    initialize resources again. Executor shutdown cancels queued work but cannot
    terminate extraction already running in a thread.
    """
    global _close_task, _resource_generation
    task = _close_task
    if task is None:
        _resource_generation += 1
        task = asyncio.create_task(_close_resources())
        _close_task = task

        def cleanup(done: asyncio.Task[None]) -> None:
            if not done.cancelled():
                # Retrieve failures even if every shutdown waiter was cancelled.
                done.exception()

        task.add_done_callback(cleanup)
    await asyncio.shield(task)


def _status_hint(status_code: int) -> str:
    """Return a short actionable hint for common HTTP error statuses."""
    if status_code == 401:
        return "authentication required; prefer an open version or another source"

    if status_code == 403:
        return "access forbidden; prefer another source rather than retrying"

    if status_code == 404:
        return "page not found; check the URL or search for a current one"

    if status_code == 429:
        return "rate limited; wait and retry, or prefer another source"

    if 500 <= status_code <= 599:
        return "remote server failed; prefer another source or retry later"

    return "prefer another source"


async def _read_limited(response: httpx.Response) -> bytes:
    """Read a streamed response under the hard post-decompression byte cap.

    Content-Length is a pre-check only. Raw bytes and bounded gzip output
    are checked independently, before unbounded decompression allocation.
    """
    content_length = response.headers.get("content-length")

    if content_length:
        try:
            declared = int(content_length)
        except ValueError:
            # Malformed Content-Length is ignored. The streaming limit below
            # remains authoritative.
            pass
        else:
            if declared > MAX_RESPONSE_BYTES:
                raise FetchError(
                    f"response too large: Content-Length={declared} bytes",
                    f"page exceeds the {MAX_RESPONSE_BYTES}-byte cap; prefer another source",
                )

    chunks: list[bytes] = []
    total = 0

    encoding = response.headers.get("content-encoding", "identity").strip().lower()
    if encoding not in {"identity", "gzip"}:
        raise FetchError(
            "unsupported content encoding",
            "server must support gzip or identity",
            kind="unsupported_content",
        )
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == "gzip" else None
    wire_total = 0
    async for chunk in response.aiter_raw():
        wire_total += len(chunk)
        if wire_total > MAX_RESPONSE_BYTES:
            raise FetchError(
                "compressed response exceeds byte limit", kind="response_too_large"
            )
        if decoder is not None:
            try:
                chunk = decoder.decompress(chunk, MAX_RESPONSE_BYTES - total + 1)
            except zlib.error as exc:
                raise FetchError(
                    "invalid gzip response", kind="invalid_content"
                ) from exc
        total += len(chunk)

        if total > MAX_RESPONSE_BYTES:
            raise FetchError(
                f"response exceeded {MAX_RESPONSE_BYTES}-byte cap after decompression",
                "prefer another source",
            )

        chunks.append(chunk)

    if decoder is not None and (not decoder.eof or decoder.unused_data):
        raise FetchError(
            "incomplete or concatenated gzip response", kind="invalid_content"
        )

    return b"".join(chunks)


def _check_url_length(url: str) -> None:
    """Reject unusable transport URLs before retrieval or cache reuse."""
    try:
        too_long = exceeds_url_limit(url)
    except (httpx.InvalidURL, UnicodeError) as exc:
        raise FetchError(
            f"invalid URL for HTTP transport: {exc}",
            "check the URL or prefer another source",
            kind="invalid_url",
        ) from exc
    if too_long:
        raise FetchError(
            f"URL exceeds {MAX_URL_CHARS} characters in input or HTTPX representation",
            "use a shorter URL or prefer another source",
            kind="invalid_url",
        )


async def _download(
    url: str, *, validate_initial: bool = True
) -> tuple[str, bytes, httpx.Headers]:
    """Download one document with per-hop SSRF validation and size caps.

    ``validate_initial=False`` skips first-hop validation only when the caller
    has validated the exact URL immediately before (fetch_page does). Every
    redirect target is always validated before its request is issued.
    """
    current_url = url
    client = _get_client()

    try:
        for hop in range(MAX_REDIRECTS + 1):
            _check_url_length(current_url)
            if validate_initial or hop > 0:
                await validate_url(current_url)

            async with (
                _get_limiter().request(current_url),
                client.stream("GET", current_url) as response,
            ):
                _check_url_length(str(response.url))
                if response.status_code in REDIRECT_STATUSES:
                    location = response.headers.get("location")

                    if not location:
                        raise FetchError(
                            f"HTTP {response.status_code} without Location header",
                            (
                                "server returned a redirect with no target; "
                                "try another source"
                            ),
                            kind="http_status",
                        )

                    if hop == MAX_REDIRECTS:
                        raise FetchError(
                            "too many redirects",
                            f"page exceeds the {MAX_REDIRECTS}-redirect limit",
                            kind="http_status",
                        )

                    # Resolve a relative Location against the effective URL.
                    # The resulting target is validated at the top of the next
                    # loop iteration before another request is issued.
                    try:
                        current_url = urljoin(str(response.url), location)
                    except ValueError as exc:
                        raise FetchError(
                            "invalid redirect URL",
                            "server returned a malformed redirect target; prefer another source",
                            kind="invalid_url",
                        ) from exc
                    continue

                if response.status_code >= 400:
                    raise FetchError(
                        f"HTTP status {response.status_code}",
                        _status_hint(response.status_code),
                        kind="http_status",
                    )

                body = await _read_limited(response)

                return str(response.url), body, response.headers

        # Defensive terminal failure. The hop == MAX_REDIRECTS branch above
        # should make this unreachable.
        raise FetchError(
            "too many redirects", "prefer another source", kind="http_status"
        )

    except SecurityError:
        # Security violations are part of the public fetch contract; never
        # normalize them into generic HTTP failures.
        raise

    except (httpx.InvalidURL, UnicodeError) as exc:
        # InvalidURL is not an HTTPError subclass. UnicodeError also covers
        # transport-side hostname encoding failures.
        raise FetchError(
            f"invalid URL for HTTP transport: {exc}",
            "check the URL or prefer another source",
            kind="invalid_url",
        ) from exc

    except httpx.HTTPError as exc:
        raise FetchError(
            f"HTTP request failed: {type(exc).__name__}: {exc}",
            "retry later or prefer another source",
            kind="http_error",
        ) from exc


def _decode_html(body: bytes, headers: httpx.Headers) -> str:
    """Use HTTP charset, then HTML/BOM detection, with replacement on errors."""
    content_type = headers.get("content-type", "")
    charset: str | None = None

    for parameter in content_type.split(";")[1:]:
        name, separator, value = parameter.partition("=")

        if separator and name.strip().lower() == "charset":
            candidate = value.strip().strip("\"'")

            if candidate:
                charset = candidate

            break

    if not isinstance(charset, str):
        markup = UnicodeDammit(body, is_html=True).unicode_markup
        if isinstance(markup, str) and markup:
            return markup
        return body.decode("utf-8", errors="replace")
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _fallback_extract(html: str) -> tuple[str, str]:
    """Extract readable text with BeautifulSoup when Trafilatura yields little."""
    soup = BeautifulSoup(html, "html.parser")

    title = ""

    if soup.title is not None:
        title = soup.title.get_text(" ", strip=True)

    for element in soup(["script", "style", "noscript", "template", "svg"]):
        element.decompose()

    text = soup.get_text("\n", strip=True)

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    return title, "\n".join(lines)


def _extract(html: str, base_url: str) -> tuple[str, str, NavigationResult]:
    """Return readable text plus independently useful bounded navigation.

    Title preference: Trafilatura metadata (og:title etc.) -> <title>.
    ``favor_precision`` is deliberate: clean research excerpts matter more
    than maximal recall, while too-small results fall back to BS4 text.
    Relative links are resolved against the final fetched URL, and comments
    are excluded from the primary article extraction.
    """
    title = ""
    navigation = extract_navigation(html, base_url)

    metadata = trafilatura.metadata.extract_metadata(html)

    if metadata and metadata.title:
        title = metadata.title.strip()

    text = (
        trafilatura.extract(
            html,
            url=base_url,
            output_format="markdown",
            include_comments=False,
            include_links=True,
            include_images=False,
            include_tables=True,
            favor_precision=True,
        )
        or ""
    ).strip()

    if len(text) < MIN_EXTRACTED_CHARS:
        fallback_title, fallback_text = _fallback_extract(html)

        if len(fallback_text) > len(text):
            text = fallback_text

        if not title:
            title = fallback_title

    if not title:
        soup = BeautifulSoup(html, "html.parser")

        if soup.title is not None:
            title = soup.title.get_text(" ", strip=True)

    return title, text, navigation


async def _fetch_page_uncached(url: str, key: str) -> FetchResult:
    """Download, extract and cache one already-validated page."""
    try:
        async with asyncio.timeout(DOWNLOAD_TIMEOUT):
            final_url, body, headers = await _download(url, validate_initial=False)
    except TimeoutError as exc:
        raise FetchError(
            "page download timed out", "prefer another source", kind="timeout"
        ) from exc

    content_type = (headers.get("content-type") or "").split(";", 1)[0].lower().strip()

    if content_type not in ALLOWED_CONTENT_TYPES:
        hint = (
            "PDF is outside the supported HTML scope; use an HTML version"
            if content_type == "application/pdf"
            else "prefer an HTML source"
        )

        raise FetchError(
            f"content type not supported: {content_type or 'unknown'}",
            hint,
            kind="unsupported_content",
        )

    html = _decode_html(body, headers)

    title, text, navigation = await _extract_bounded(html, final_url)
    title = truncate_metadata(title, MAX_TITLE_CHARS)

    # Text adequacy is a reading-policy decision. Short HTML pages can still
    # provide useful navigation to web_links.
    text_sufficient = len(text) >= MIN_EXTRACTED_CHARS
    text_truncated = len(text) > MAX_TEXT_CHARS
    text = text[:MAX_TEXT_CHARS]

    value = CachedPage(
        url=final_url,
        title=title,
        text=text,
        text_truncated=text_truncated,
        links=navigation.links,
        links_truncated=navigation.links_truncated,
        text_sufficient=text_sufficient,
    )

    # TTL belongs to the cache instance.
    fetch_cache.set(key, value)

    # Alias the redirect target so fetching it directly reuses the extraction.
    # Both entries are written in the same tick -> near-synchronous expiry.
    final_key = normalize_url(final_url)

    if final_key != key:
        fetch_cache.set(final_key, value)

    return FetchResult(
        url=final_url,
        title=title,
        text=text,
        text_truncated=text_truncated,
        links=navigation.links,
        links_truncated=navigation.links_truncated,
        text_sufficient=text_sufficient,
    )


async def fetch_page(url: str) -> FetchResult:
    """Fetch and extract a page with validated single-flight coalescing.

    Validation precedes both cache reuse and in-flight sharing. This is a
    security invariant: canonical keys collapse URL variants, so unsafe input
    must never join a task created for a safe URL merely because the cache key
    matches. Concurrent safe callers for the same canonical URL share one
    download/extraction task. Canceling one waiter does not cancel shared work.

    Raises:
        SecurityError: If the initial URL or a redirect target is unsafe.
        FetchError: For expected URL-budget, transport, HTTP status, content,
            download-timeout, or shutdown failures.

    Low-text pages are returned with ``text_sufficient=False``, determined before
    retention truncation. Reading and collection consumers decide whether that
    text is suitable; link discovery remains available. Unexpected extraction
    errors propagate rather than being converted into insufficient-text errors.
    """
    _ensure_open()
    generation = _resource_generation
    _check_url_length(url)
    await validate_url(url)
    _ensure_open()
    if generation != _resource_generation:
        raise FetchError("fetch interrupted by shutdown", kind="shutdown")

    key = normalize_url(url)
    cached = fetch_cache.get(key)

    if cached is not None:
        return FetchResult(
            url=cached.url,
            title=cached.title,
            text=cached.text,
            cache_hit=True,
            text_truncated=cached.text_truncated,
            links=cached.links,
            links_truncated=cached.links_truncated,
            text_sufficient=cached.text_sufficient,
        )

    task = _fetch_flights.get(key)
    if task is None:
        task = asyncio.create_task(_fetch_page_uncached(url, key))
        _fetch_flights[key] = task

        def cleanup(done: asyncio.Task[FetchResult]) -> None:
            if _fetch_flights.get(key) is done:
                _fetch_flights.pop(key, None)
            if not done.cancelled():
                # Mark an exception retrieved even if every waiter was canceled.
                done.exception()

        task.add_done_callback(cleanup)

    return await asyncio.shield(task)
