"""MCP tools: web_search, web_fetch, web_links, research_collect.

Tools return validated models serialized as flat JSON objects. Expected failures use
{"error", "hint"} instead of opaque MCP tool errors; unexpected programming
errors are deliberately not swallowed.

Tool docstrings are part of the agent-facing contract: FastMCP exposes them
as tool descriptions, so they carry usage semantics, not just prose.
"""

import asyncio
import os
import re
import time
from collections.abc import Iterable
from copy import deepcopy
from hashlib import sha256
from typing import Annotated, Final

import httpx
from pydantic import Field

from mcp_search.cache import normalize_url, search_cache
from mcp_search.config import (
    DEFAULT_ENGINES,
    DEFAULT_EXPAND_CHARS,
    DEFAULT_MAX_FETCH_CHARS,
    DEFAULT_MAX_QUERIES,
    DEFAULT_MAX_RESULTS,
    DEFAULT_MAX_SOURCES,
    DEFAULT_SEARCH_INTERVAL,
    DEFAULT_SEARXNG_URL,
    positive_float,
    positive_int,
)
from mcp_search.excerpt import classify_source_type, select_excerpts
from mcp_search.fetcher import FetchError, fetch_page
from mcp_search.metadata_limits import (
    MAX_ENGINE_CHARS,
    MAX_ENGINE_NAME_CHARS,
    MAX_ERROR_CHARS,
    MAX_GAP_CHARS,
    MAX_HINT_CHARS,
    MAX_SNIPPET_CHARS,
    MAX_TITLE_CHARS,
    MAX_UNRESPONSIVE_ENGINES,
    truncate_metadata,
)
from mcp_search.models import (
    CONTENT_HASH_PATTERN,
    CollectResponse,
    ContentChangedError,
    ExpectedContentHash,
    FetchAction,
    FetchResponse,
    LinkAction,
    LinksChangedError,
    LinksResponse,
    SearchResponse,
    WebFetchArguments,
    WebLinksArguments,
)
from mcp_search.navigation import (
    DEFAULT_LINKS_PER_RESPONSE,
    MAX_LINKS_PER_RESPONSE,
    MAX_URL_CHARS,
    link_payload,
    links_hash,
)
from mcp_search.security import SecurityError

VALID_ENGINES: Final = tuple(
    engine.strip()
    for engine in os.environ.get("MCP_SEARCH_ENGINES", ",".join(DEFAULT_ENGINES)).split(
        ","
    )
    if engine.strip()
)
VALID_TIME_RANGES: Final = {"day", "week", "month", "year"}
VALID_SAFE_SEARCH: Final = {0, 1, 2}

MAX_RESULTS_CAP: Final = positive_int("MAX_RESULTS", DEFAULT_MAX_RESULTS)
MAX_FETCH_CHARS: Final = positive_int("MAX_FETCH_CHARS", DEFAULT_MAX_FETCH_CHARS)
MAX_SOURCES_CAP: Final = positive_int("MAX_SOURCES", DEFAULT_MAX_SOURCES)
MAX_QUERIES: Final = positive_int("MAX_QUERIES", DEFAULT_MAX_QUERIES)
EXPAND_CHARS: Final = positive_int("EXPAND_CHARS", DEFAULT_EXPAND_CHARS)

# Public request-shape safety ceilings. These bound work before configurable
# operational budgets (such as MAX_SOURCES_CAP) are applied.
MAX_QUERY_CHARS: Final = 4096
MAX_TOPIC_CHARS: Final = 4096
MAX_LANGUAGE_CHARS: Final = 64
MAX_DOMAIN_CHARS: Final = 253
MAX_DOMAIN_FILTERS: Final = 50
MAX_EXPLICIT_URLS: Final = 100

SEARCH_PAUSE_SECONDS: Final = positive_float("SEARCH_INTERVAL", DEFAULT_SEARCH_INTERVAL)

_searxng_client: httpx.AsyncClient | None = None

_search_lock: asyncio.Lock | None = None
_last_search_at = 0.0


def _searxng_url() -> str:
    """Return the configured SearXNG base URL.

    The environment is read on each call. The shared HTTP client itself does
    not snapshot this URL because the URL is supplied per request.
    """
    return os.environ.get("MCP_SEARCH_SEARXNG_URL", DEFAULT_SEARXNG_URL).rstrip("/")


def _get_searxng_client() -> httpx.AsyncClient:
    """Return the shared client for the local SearXNG instance."""
    global _searxng_client

    client = _searxng_client
    if client is None or client.is_closed:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5, read=20, write=10, pool=5),
            # SearXNG is expected to be loopback. Never inherit HTTP(S)_PROXY
            # or system proxy settings: the proxy would become the actual
            # transport boundary instead of this process.
            trust_env=False,
        )
        _searxng_client = client

    return client


async def close_searxng_client() -> None:
    """Close the shared SearXNG client.

    Idempotent, mirroring fetcher.close_http_client(). The server lifecycle
    must call both shutdown functions.
    """
    global _searxng_client, _search_lock, _last_search_at

    client = _searxng_client
    _searxng_client = None
    _search_lock = None
    _last_search_at = 0.0

    if client is not None and not client.is_closed:
        await client.aclose()


def _get_search_lock() -> asyncio.Lock:
    """Return the lazily-created global search serialization lock.

    Runtime synchronization state is created lazily rather than at import
    time. asyncio synchronization primitives can become bound to the event
    loop that needs them; tests that intentionally use fresh event loops must
    reset all module-level asyncio primitive state between loops.
    """
    global _search_lock

    lock = _search_lock
    if lock is None:
        lock = asyncio.Lock()
        _search_lock = lock

    return lock


def _error(error: str, hint: str = "") -> dict[str, object]:
    """Build the common structured tool-error payload."""
    return {
        "error": truncate_metadata(error, MAX_ERROR_CHARS),
        "hint": truncate_metadata(hint, MAX_HINT_CHARS),
    }


def _too_long(value: str | None, limit: int) -> bool:
    return value is not None and len(value) > limit


def _validate_search_args(
    engines: list[str] | None, time_range: str | None, safe_search: int | None
) -> dict[str, object] | None:
    """Reject invalid search parameters with actionable errors."""
    if engines:
        if len(engines) > len(VALID_ENGINES):
            return _error(f"at most {len(VALID_ENGINES)} engines may be requested")

        unknown = [engine for engine in engines if engine not in VALID_ENGINES]

        if unknown:
            return _error(
                f"unknown engines: {', '.join(unknown)}",
                f"valid engines: {', '.join(VALID_ENGINES)}",
            )

    if time_range is not None and time_range not in VALID_TIME_RANGES:
        return _error(
            f"invalid time_range: {time_range}",
            f"valid values: {', '.join(sorted(VALID_TIME_RANGES))}",
        )

    if safe_search is not None and safe_search not in VALID_SAFE_SEARCH:
        return _error("invalid safe_search", "valid values: 0, 1, 2")

    return None


def _build_query(query: str, domain: str | None, excluded: Iterable[str] | None) -> str:
    """Append site: / -site: operators to a search query.

    Exclusion operators are not honored by every configured search engine.
    Domain values are intentionally not interpreted as security-sensitive
    input: malformed operators can degrade search quality but do not control
    outbound fetching.
    """
    parts = [query.strip()]

    if domain:
        parts.append(f"site:{domain.strip()}")

    for item in excluded or ():
        if item.strip():
            parts.append(f"-site:{item.strip()}")

    return " ".join(part for part in parts if part)


def _normalize_unresponsive(raw: object) -> list[str]:
    """Normalize SearXNG unresponsive-engine data.

    SearXNG commonly returns [["engine", "reason"], ...] or ["engine", ...].
    """
    result: list[str] = []

    if not isinstance(raw, list):
        return result

    for item in raw[:MAX_UNRESPONSIVE_ENGINES]:
        if isinstance(item, (list, tuple)) and item:
            name = str(item[0])
        else:
            name = str(item)
        result.append(truncate_metadata(name, MAX_ENGINE_NAME_CHARS))

    return result


async def web_search(
    query: Annotated[
        str,
        Field(
            max_length=MAX_QUERY_CHARS,
            description="Search terms. For several query variants and fetched excerpts, use research_collect instead.",
        ),
    ],
    engines: Annotated[
        list[str] | None,
        Field(
            max_length=len(VALID_ENGINES),
            description=f"Optional engine subset: {', '.join(VALID_ENGINES)}. Omit to use SearXNG defaults.",
        ),
    ] = None,
    max_results: Annotated[
        int,
        Field(
            description=f"Requested candidates. Default 10; configured cap {MAX_RESULTS_CAP}. This is a result limit, not search pagination."
        ),
    ] = 10,
    language: Annotated[
        str | None,
        Field(
            max_length=MAX_LANGUAGE_CHARS,
            description="Language/locale such as en or ru. Omit for any language.",
        ),
    ] = None,
    time_range: Annotated[
        str | None,
        Field(description="Optional recency filter: day, week, month or year."),
    ] = None,
    safe_search: Annotated[
        int | None,
        Field(description="0=off, 1=moderate, 2=strict. Omit for provider defaults."),
    ] = None,
    domain: Annotated[
        str | None,
        Field(
            max_length=MAX_DOMAIN_CHARS,
            description="Include site:domain in the query, e.g. docs.python.org. Use a hostname, not a page URL. Can be combined with exclude_domains.",
        ),
    ] = None,
    exclude_domains: Annotated[
        list[Annotated[str, Field(max_length=MAX_DOMAIN_CHARS)]] | None,
        Field(
            max_length=MAX_DOMAIN_FILTERS,
            description="Exclude domains with -site: operators, e.g. ['pinterest.com', 'example.org']. Provider support varies; verify returned URLs.",
        ),
    ] = None,
) -> SearchResponse:
    """Discover candidate sources through search; this does not fetch page content.

    USE THIS when the needed source or URL is not yet known, when you need a new
    independent source, or when search-engine discovery itself is required.
    DO NOT search again merely to find another page inside a strong source when
    that page is likely linked from the current page; use web_links instead.

    Domain filtering example: web_search(query="asyncio", domain="python.org",
    exclude_domains=["discuss.python.org"], max_results=20). Domain operators
    depend on the provider. Search pagination is not supported.

    Results are candidates, not verified page evidence: snippet is a search-engine
    preview and result.url has not been fetched. For a candidate:
    - web_links(url=result.url): inspect chapters, pagination, references or related
      pages exposed by that source without crawling them;
    - web_fetch(url=result.url, max_chars=500): preview/read the selected document;
    - research_collect(urls=[...]): collect bounded evidence from selected URLs.

    Returns results, query_used, unresponsive_engines and cached. Always inspect
    unresponsive_engines: nonempty means incomplete search coverage. Expected
    failures return {error, hint}.
    """
    if _too_long(query, MAX_QUERY_CHARS):
        return SearchResponse.model_validate(
            _error(f"query exceeds {MAX_QUERY_CHARS} characters")
        )
    if _too_long(language, MAX_LANGUAGE_CHARS):
        return SearchResponse.model_validate(
            _error(f"language exceeds {MAX_LANGUAGE_CHARS} characters")
        )
    if _too_long(domain, MAX_DOMAIN_CHARS):
        return SearchResponse.model_validate(
            _error(f"domain exceeds {MAX_DOMAIN_CHARS} characters")
        )
    if exclude_domains is not None:
        if len(exclude_domains) > MAX_DOMAIN_FILTERS:
            return SearchResponse.model_validate(
                _error(f"at most {MAX_DOMAIN_FILTERS} exclude_domains are allowed")
            )
        if any(_too_long(item, MAX_DOMAIN_CHARS) for item in exclude_domains):
            return SearchResponse.model_validate(
                _error(
                    f"exclude_domains entries may be at most {MAX_DOMAIN_CHARS} characters"
                )
            )

    validation_error = _validate_search_args(engines, time_range, safe_search)

    if validation_error:
        return SearchResponse.model_validate(validation_error)

    if not query.strip():
        return SearchResponse.model_validate(_error("query must not be empty"))

    query_used = _build_query(query, domain, exclude_domains)

    limit = min(max(1, max_results), MAX_RESULTS_CAP)

    if max_results < 1:
        return SearchResponse.model_validate(_error("max_results must be >= 1"))

    cache_key = (
        _searxng_url(),
        query_used,
        tuple(engines or ()),
        language,
        time_range,
        safe_search,
        limit,
    )

    cached = search_cache.get(cache_key)

    if cached is not None:
        return SearchResponse.model_validate({**deepcopy(cached), "cached": True})

    global _last_search_at

    async with _get_search_lock():
        # Double-check after serialization: an identical concurrent call may
        # have populated the cache while this coroutine waited.
        cached = search_cache.get(cache_key)

        if cached is not None:
            return SearchResponse.model_validate({**deepcopy(cached), "cached": True})

        while (wait := _last_search_at + SEARCH_PAUSE_SECONDS - time.monotonic()) > 0:
            await asyncio.sleep(wait)

        params: dict[str, str] = {"q": query_used, "format": "json"}

        if engines:
            params["engines"] = ",".join(engines)

        if language:
            params["language"] = language

        if time_range:
            params["time_range"] = time_range

        if safe_search is not None:
            params["safe_search"] = str(safe_search)

        try:
            response = await _get_searxng_client().get(
                f"{_searxng_url()}/search", params=params
            )

        except (httpx.InvalidURL, UnicodeError) as exc:
            return SearchResponse.model_validate(
                _error(
                    f"invalid SearXNG URL: {exc}",
                    (
                        "check MCP_SEARCH_SEARXNG_URL; expected a base URL such as "
                        "http://127.0.0.1:8081"
                    ),
                )
            )

        except httpx.HTTPError as exc:
            return SearchResponse.model_validate(
                _error(
                    f"SearXNG unreachable: {type(exc).__name__}: {exc}",
                    "verify that the local SearXNG container is running",
                )
            )

        finally:
            _last_search_at = time.monotonic()

    if response.status_code != 200:
        return SearchResponse.model_validate(
            _error(
                f"SearXNG HTTP {response.status_code}",
                (
                    "403 usually means the limiter is active or the settings "
                    "mount is empty; check searxng/settings.yml "
                    "(limiter: false, search.formats: [html, json])"
                ),
            )
        )

    try:
        data = response.json()
    except ValueError as exc:
        return SearchResponse.model_validate(
            _error(f"SearXNG returned non-JSON: {exc}")
        )

    if not isinstance(data, dict):
        return SearchResponse.model_validate(
            _error(
                "SearXNG returned an unexpected JSON structure",
                "expected a JSON object containing a results list",
            )
        )

    results_raw = data.get("results")
    if not isinstance(results_raw, list):
        return SearchResponse.model_validate(
            _error(
                "SearXNG returned no results list", "check the SearXNG response format"
            )
        )

    results: list[dict[str, object]] = []
    seen: set[str] = set()

    if isinstance(results_raw, list):
        for item in results_raw:
            if not isinstance(item, dict):
                continue

            url = str(item.get("url") or "")

            if not url or len(url) > MAX_URL_CHARS:
                continue

            key = normalize_url(url)

            if key in seen:
                continue

            seen.add(key)

            engines_field = item.get("engines", [])

            engine = (
                ",".join(map(str, engines_field))
                if isinstance(engines_field, list)
                else str(engines_field or "")
            )

            results.append(
                {
                    "title": truncate_metadata(
                        str(item.get("title") or ""), MAX_TITLE_CHARS
                    ),
                    "url": url,
                    "snippet": truncate_metadata(
                        str(item.get("content") or ""), MAX_SNIPPET_CHARS
                    ),
                    "engine": truncate_metadata(engine, MAX_ENGINE_CHARS),
                    "source_type": classify_source_type(url),
                }
            )

            if len(results) >= limit:
                break

    result: dict[str, object] = {
        "results": results,
        "unresponsive_engines": _normalize_unresponsive(
            data.get("unresponsive_engines")
        ),
        "query_used": query_used,
        "cached": False,
    }

    # TTL belongs to the cache instance.
    search_cache.set(cache_key, deepcopy(result))

    return SearchResponse.model_validate(result)


def _cut_at_paragraph(text: str, limit: int) -> str:
    """Cut at a paragraph boundary near limit, never past it.

    Falling back to a hard cut when no boundary lies in the first half of the
    requested window keeps slices useful and non-empty.
    """
    if len(text) <= limit:
        return text

    candidate = text[:limit]
    boundary = candidate.rfind("\n\n")

    if boundary > limit // 2:
        return candidate[:boundary].rstrip()

    return candidate


def _links_action(
    url: str,
    same_origin: bool | None,
    start_index: int,
    max_links: int,
    navigation_hash: str,
) -> LinkAction:
    """Build a data-only, version-checked link continuation."""
    return LinkAction(
        tool="web_links",
        arguments=WebLinksArguments(
            url=url,
            same_origin=same_origin,
            start_index=start_index,
            max_links=max_links,
            expected_links_hash=navigation_hash,
        ),
    )


def _fetch_action(
    url: str, start_offset: int, max_chars: int, content_hash: str
) -> FetchAction:
    """Build a data-only, version-checked action without fetching or interpreting text."""
    return FetchAction(
        tool="web_fetch",
        arguments=WebFetchArguments(
            url=url,
            start_offset=start_offset,
            max_chars=max_chars,
            expected_content_hash=content_hash,
        ),
    )


async def web_fetch(
    url: Annotated[
        str,
        Field(
            max_length=MAX_URL_CHARS,
            description="HTTP(S) page URL, a search result.url or research source.url. Supports HTML/XHTML; no PDF or JavaScript rendering.",
        ),
    ],
    start_offset: Annotated[
        int,
        Field(
            description="Unicode-character offset; default 0. Ready continuation/expand arguments provide it. For manual reading, use next_start or excerpt.start_char."
        ),
    ] = 0,
    max_chars: Annotated[
        int,
        Field(
            description=f"Maximum returned characters: default 10000, configured cap {MAX_FETCH_CHARS}. Use 500 for preview. Ready actions include a budget; smaller output saves context, not the initial download."
        ),
    ] = 10_000,
    expected_content_hash: Annotated[
        ExpectedContentHash | None,
        Field(
            description="Optional retained-text version guard. Ready actions supply it; mismatch returns content_changed without a slice. Omit for unguarded reading."
        ),
    ] = None,
) -> FetchResponse:
    """Read one selected HTML document as bounded Markdown text.

    USE THIS when you already know which document you want to read, preview, or
    expand around a collected excerpt. If you know the source but need to find
    its chapter, appendix, next page, reference, or related document first, use web_links instead.
    If you do not yet know a source, use web_search.

    Preview with max_chars=500 to limit model context; this does not reduce the
    initial network download. When more retained text is useful, copy
    continuation.arguments into the indicated tool rather than recalculating the
    next offset. Null continuation means the retained text has ended.

    continuation and excerpt.expand use expected_content_hash. If the retained
    text version changed, content_changed returns no slice: reacquire the document
    and choose coordinates again. A matching hash protects coordinates, not
    origin freshness.

    A page can have too little readable text for web_fetch while still exposing
    useful ordinary HTML links through web_links; treat such pages as possible
    navigation hubs instead of assuming the source has no usable structure.

    Returns content, title, final URL, source category, Unicode-coordinate paging,
    cache/hash fields and continuation. truncated means more retained text can be
    continued; text_truncated means a tail was discarded by the hard retention
    ceiling and cannot be recovered by pagination. Expected failures return
    {error, hint}.
    """
    if len(url) > MAX_URL_CHARS:
        return FetchResponse.model_validate(
            _error(f"url exceeds {MAX_URL_CHARS} characters")
        )
    if start_offset < 0:
        return FetchResponse.model_validate(_error("start_offset must be >= 0"))

    if max_chars < 1:
        return FetchResponse.model_validate(_error("max_chars must be >= 1"))

    if (
        expected_content_hash is not None
        and re.fullmatch(CONTENT_HASH_PATTERN, expected_content_hash) is None
    ):
        return FetchResponse.model_validate(
            _error("expected_content_hash must be 64 lowercase hexadecimal characters")
        )

    try:
        page = await fetch_page(url)

    except SecurityError as exc:
        return FetchResponse.model_validate(_error("blocked_url", str(exc)))

    except FetchError as exc:
        return FetchResponse.model_validate(_error(exc.error, exc.hint))

    if not page.text_sufficient:
        return FetchResponse.model_validate(
            _error(
                "Page returned too little extractable text",
                "likely JavaScript-rendered or intentionally short; use web_links for page navigation or prefer another readable source",
            )
        )

    content_hash = sha256(page.text.encode("utf-8")).hexdigest()
    if expected_content_hash is not None and expected_content_hash != content_hash:
        return FetchResponse(
            ContentChangedError(
                error="content_changed",
                hint="Retained extracted text differs from the expected version. No slice was returned. Reacquire the source material without the old hash and choose coordinates again; this does not establish that the old citation was false.",
            )
        )

    total = len(page.text)

    limit = min(max_chars, MAX_FETCH_CHARS)

    start = min(start_offset, total)

    content = _cut_at_paragraph(page.text[start:], limit)

    end = start + len(content)
    truncated = end < total

    return FetchResponse.model_validate(
        {
            "title": truncate_metadata(page.title, MAX_TITLE_CHARS),
            "url": page.url,
            "content": content,
            "total_chars": total,
            "next_start": end if truncated else None,
            "truncated": truncated,
            "cache_hit": page.cache_hit,
            "source_type": classify_source_type(page.url),
            "text_truncated": page.text_truncated,
            "content_hash": content_hash,
            "continuation": _fetch_action(page.url, end, limit, content_hash)
            if truncated
            else None,
        }
    )


async def web_links(
    url: Annotated[
        str,
        Field(
            max_length=MAX_URL_CHARS,
            description="Known HTTP(S) HTML page whose exposed navigation you want to inspect. Use after finding a useful source when you need chapters, pagination, references or related pages. The page itself is fetched safely; returned destinations are not contacted until selected later.",
        ),
    ],
    same_origin: Annotated[
        bool | None,
        Field(
            description="Navigation filter relative to the final fetched page. true=same scheme+normalized host+effective port only; false=cross-origin only; null=keep both (default, best when external references may matter). Filtering happens before pagination."
        ),
    ] = None,
    start_index: Annotated[
        int,
        Field(
            description="Zero-based index in the filtered retained link list. Ready continuation arguments provide it."
        ),
    ] = 0,
    max_links: Annotated[
        int,
        Field(
            description=f"Maximum links returned: default {DEFAULT_LINKS_PER_RESPONSE}, hard cap {MAX_LINKS_PER_RESPONSE}. Ready continuation preserves the effective budget."
        ),
    ] = DEFAULT_LINKS_PER_RESPONSE,
    expected_links_hash: Annotated[
        str | None,
        Field(
            description="Optional retained-link-list version guard. Ready continuations supply it; mismatch returns links_changed without using the old index."
        ),
    ] = None,
) -> LinksResponse:
    """Navigate from a known HTML page to pages that it explicitly links.

    USE THIS when you already found a useful source but need its structure:
    documentation sections, report chapters, table-of-contents entries,
    next/previous publication pages, appendices, references, datasets, standards,
    or related pages. It is the bridge between web_search discovery and web_fetch reading.
    Prefer this over another search when the desired page is plausibly
    linked from the source you already have.

    This is NOT a crawler or browser. It inspects ordinary <a href> links in this
    one fetched HTML page only. It does not follow them, click controls, execute
    JavaScript, submit forms, DNS-resolve destinations, or safety-approve them.
    Selecting a returned URL for web_fetch/web_links later triggers the normal
    outbound SSRF policy.

    same_origin=true keeps only links with the same scheme, normalized hostname
    and effective port as the final fetched page. Leave same_origin=null when
    external citations or primary sources may matter; same origin does not mean
    same organization, and cross-origin does not mean untrusted.

    The retained list preserves document order after deterministic URL
    deduplication. Fragments remain part of link identity. same_document=true
    means only that the destination has the same document identity ignoring the
    fragment; web_fetch still navigates text by Unicode offsets, not HTML anchors.

    Filtering happens BEFORE pagination. Copy continuation.arguments to retrieve
    the next retained link page. links_hash versions the whole retained ordered
    list before filtering/pagination; links_changed means the old start_index must
    not be reused. continuation means more retained links exist; links_truncated
    means some admissible links were lost to hard page-level resource ceilings
    and continuation cannot recover them.

    Each link returns url, best-effort label, rel, fragment, same_origin and
    same_document. An empty links list does not prove that the site has no other
    pages. Expected failures return {error, hint}.
    """
    if len(url) > MAX_URL_CHARS:
        return LinksResponse.model_validate(
            _error(f"url exceeds {MAX_URL_CHARS} characters")
        )
    if start_index < 0:
        return LinksResponse.model_validate(_error("start_index must be >= 0"))
    if max_links < 1:
        return LinksResponse.model_validate(_error("max_links must be >= 1"))
    if (
        expected_links_hash is not None
        and re.fullmatch(CONTENT_HASH_PATTERN, expected_links_hash) is None
    ):
        return LinksResponse.model_validate(
            _error("expected_links_hash must be 64 lowercase hexadecimal characters")
        )

    try:
        page = await fetch_page(url)
    except SecurityError as exc:
        return LinksResponse.model_validate(_error("blocked_url", str(exc)))
    except FetchError as exc:
        return LinksResponse.model_validate(_error(exc.error, exc.hint))

    navigation_hash = links_hash(page.links)
    if expected_links_hash is not None and expected_links_hash != navigation_hash:
        return LinksResponse(
            LinksChangedError(
                error="links_changed",
                hint="Retained navigation differs from the expected version. No stale list index was used. Reacquire links without the old hash before continuing.",
            )
        )

    filtered = [
        link
        for link in page.links
        if same_origin is None or link.same_origin is same_origin
    ]
    total = len(filtered)
    start = min(start_index, total)
    limit = min(max_links, MAX_LINKS_PER_RESPONSE)
    end = min(start + limit, total)
    selected = filtered[start:end]
    next_index = end if end < total else None

    return LinksResponse.model_validate(
        {
            "url": page.url,
            "links_hash": navigation_hash,
            "links": [link_payload(link) for link in selected],
            "total_retained_matching": total,
            "next_start_index": next_index,
            "links_truncated": page.links_truncated,
            "cache_hit": page.cache_hit,
            "continuation": _links_action(
                page.url, same_origin, end, limit, navigation_hash
            )
            if next_index is not None
            else None,
        }
    )


def _gap_for_fetch_error(url: str, exc: FetchError) -> str:
    """Return a deterministic research gap from a fetcher's machine kind."""
    if exc.kind == "js_page":
        return f"{url}: too little extractable text (likely JS-rendered)"

    return f"{url}: {exc.error}"


def _source_id(url: str) -> str:
    """Return a stable identifier derived from a canonical final URL.

    The same normalized final URL produces the same identifier across calls
    and server restarts. The identifier does not assert that distinct URLs
    cannot contain the same underlying document.
    """
    canonical = normalize_url(url)

    digest = sha256(canonical.encode("utf-8")).hexdigest()[:16]

    return f"src_{digest}"


def _search_candidate(result: dict[object, object]) -> dict[str, str] | None:
    """Convert one SearXNG result payload into a research candidate."""
    url = result.get("url")

    if not isinstance(url, str) or not url or len(url) > MAX_URL_CHARS:
        return None

    title = result.get("title")
    snippet = result.get("snippet")
    return {
        "url": url,
        "title": truncate_metadata(
            title if isinstance(title, str) else "", MAX_TITLE_CHARS
        ),
        "snippet": truncate_metadata(
            snippet if isinstance(snippet, str) else "", MAX_SNIPPET_CHARS
        ),
    }


async def research_collect(
    topic: Annotated[
        str | None,
        Field(
            max_length=MAX_TOPIC_CHARS,
            description="Optional topic used only to rank excerpts alongside queries. Does not initiate a search without queries.",
        ),
    ] = None,
    queries: Annotated[
        list[Annotated[str, Field(max_length=MAX_QUERY_CHARS)]] | None,
        Field(
            max_length=MAX_QUERIES,
            description=f"Your search variants, normally 2-3; at most {MAX_QUERIES}. The server does not generate queries. May be combined with explicit URLs.",
        ),
    ] = None,
    urls: Annotated[
        list[Annotated[str, Field(max_length=MAX_URL_CHARS)]] | None,
        Field(
            max_length=MAX_EXPLICIT_URLS,
            description=f"Exact source URLs to fetch first; useful after web_search with domain/exclude_domains. Supply urls and/or queries. At most {MAX_EXPLICIT_URLS} input URLs; max_sources still controls the fetch budget.",
        ),
    ] = None,
    max_sources: Annotated[
        int,
        Field(
            description=f"Candidate fetch budget: default 5, configured cap {MAX_SOURCES_CAP}. Failed/duplicate candidates can leave fewer successful sources. Explicit URLs take priority."
        ),
    ] = 5,
    language: Annotated[
        str | None,
        Field(
            max_length=MAX_LANGUAGE_CHARS,
            description="Language/locale forwarded to search; unused in URL-only mode.",
        ),
    ] = None,
    time_range: Annotated[
        str | None,
        Field(
            description="Search recency: day, week, month or year. Does not assert a source publication date."
        ),
    ] = None,
) -> CollectResponse:
    """Collect bounded evidence from several selected or searched sources.

    USE THIS for multi-source evidence gathering when you have explicit URLs,
    several search formulations, or both. It searches/fetches candidate documents,
    extracts literal passages and reports acquisition gaps. It does NOT crawl links
    found inside those documents. If a strong source must first be navigated to a
    chapter, appendix or related page, use web_links and then pass the selected
    URLs here or to web_fetch.

    Supply queries=["variant one", "variant two"] and/or urls=["https://..."].
    topic only ranks excerpts; topic alone does not search. Explicit URLs consume
    the source budget first. If they already fill max_sources, no search is run.
    Remaining candidate slots are distributed round-robin across query variants.
    For domain/exclude_domains filtering, use web_search first and pass selected
    result URLs here.

    Returns raw material, not synthesis: query_variants, sources and gaps. Each
    source has stable source_id, final URL, source_type, content_hash,
    text_truncated and literal excerpts with Unicode offsets. BM25 selects passages;
    source_type and ranking are not credibility judgments.

    For more context around an excerpt, copy excerpt.expand.arguments into the
    indicated tool; URL, offset, budget and expected_content_hash are already
    supplied. content_changed returns no stale-coordinate slice.

    Always inspect gaps before judging coverage. They can report failed/empty
    searches, unresponsive engines, blocked/unreadable pages, insufficient text,
    redirect duplicates, omitted candidates and truncation. Empty gaps do not prove
    topic completeness. Expected request failures return {error, hint}; individual
    source failures can coexist with successful sources.
    """
    if _too_long(topic, MAX_TOPIC_CHARS):
        return CollectResponse.model_validate(
            _error(f"topic exceeds {MAX_TOPIC_CHARS} characters")
        )
    if _too_long(language, MAX_LANGUAGE_CHARS):
        return CollectResponse.model_validate(
            _error(f"language exceeds {MAX_LANGUAGE_CHARS} characters")
        )
    if queries is not None:
        if len(queries) > MAX_QUERIES:
            return CollectResponse.model_validate(
                _error(f"at most {MAX_QUERIES} queries per collection")
            )
        if any(_too_long(query, MAX_QUERY_CHARS) for query in queries):
            return CollectResponse.model_validate(
                _error(f"queries may be at most {MAX_QUERY_CHARS} characters each")
            )
    if urls is not None:
        if len(urls) > MAX_EXPLICIT_URLS:
            return CollectResponse.model_validate(
                _error(f"at most {MAX_EXPLICIT_URLS} explicit URLs per collection")
            )
        if any(_too_long(url, MAX_URL_CHARS) for url in urls):
            return CollectResponse.model_validate(
                _error(f"URLs may be at most {MAX_URL_CHARS} characters each")
            )

    clean_queries = [
        query.strip() for query in (queries or []) if query and query.strip()
    ]

    clean_urls = [url.strip() for url in (urls or []) if url and url.strip()]

    if max_sources < 1:
        return CollectResponse.model_validate(_error("max_sources must be >= 1"))

    if not clean_queries and not clean_urls:
        return CollectResponse.model_validate(
            _error(
                "nothing to collect",
                (
                    "pass queries (search mode) or urls (collect mode), "
                    "optionally topic for excerpt ranking"
                ),
            )
        )

    if time_range is not None and time_range not in VALID_TIME_RANGES:
        return CollectResponse.model_validate(
            _error(
                f"invalid time_range: {time_range}",
                f"valid values: {', '.join(sorted(VALID_TIME_RANGES))}",
            )
        )

    limit = min(max(1, max_sources), MAX_SOURCES_CAP)

    gaps: list[str] = []

    # Explicit URLs have first claim on the source budget.
    explicit_candidates: list[dict[str, str]] = []
    explicit_seen: set[str] = set()

    for url in clean_urls:
        # Before URL validation, deduplicate exact input only. Canonicalizing here
        # could let an invalid variant (for example one with credentials) suppress
        # a later valid URL that normalizes to the same cache key. Final fetched
        # URLs are still canonically deduplicated below.
        if url in explicit_seen:
            continue

        explicit_seen.add(url)

        explicit_candidates.append({"url": url, "title": "", "snippet": ""})

    if len(explicit_candidates) > limit:
        gaps.append(
            f"{len(explicit_candidates) - limit} explicit URLs omitted by max_sources"
        )

    # Preserve a separate candidate pool per query. Applying the global source
    # cap while processing the first query would bias collection toward it.
    query_pools: list[list[dict[str, str]]] = []

    # Searches cannot contribute when explicit candidates already consume the
    # entire candidate budget. Preserve query_variants in the response, but do
    # not spend provider calls on candidates that cannot be selected.
    searchable_queries = clean_queries if len(explicit_candidates) < limit else []

    for query in searchable_queries:
        search = (
            await web_search(query, language=language, time_range=time_range)
        ).model_dump()

        if "error" in search:
            gaps.append(f"query '{query}': {search['error']}")
            query_pools.append([])
            continue

        results_raw = search.get("results", [])

        if search.get("unresponsive_engines"):
            gaps.append(
                f"query '{query}': unresponsive engines: "
                + ", ".join(search["unresponsive_engines"])
            )

        if not isinstance(results_raw, list) or not results_raw:
            gaps.append(f"query '{query}': 0 results")
            query_pools.append([])
            continue

        pool: list[dict[str, str]] = []
        pool_seen: set[str] = set()

        for result in results_raw:
            if not isinstance(result, dict):
                continue

            candidate = _search_candidate(result)

            if candidate is None:
                continue

            key = normalize_url(candidate["url"])

            if key in pool_seen:
                continue

            pool_seen.add(key)
            pool.append(candidate)

            # No one query can contribute more useful candidates than the
            # total source budget.
            if len(pool) >= limit:
                break

        query_pools.append(pool)

    selected: list[dict[str, str]] = []
    selected_seen: set[str] = set()

    for candidate in explicit_candidates:
        if len(selected) >= limit:
            break

        # Keep pre-fetch dedup exact. Canonical equivalence is trustworthy only
        # after URL validation/fetching; final URLs are deduplicated below.
        key = candidate["url"]

        if key in selected_seen:
            continue

        selected_seen.add(key)
        selected.append(candidate)

    # Fill remaining capacity fairly: one candidate from each query per pass.
    positions = [0] * len(query_pools)

    while len(selected) < limit:
        progressed = False

        for pool_index, pool in enumerate(query_pools):
            while positions[pool_index] < len(pool):
                candidate = pool[positions[pool_index]]
                positions[pool_index] += 1

                key = candidate["url"]

                if key in selected_seen:
                    continue

                selected_seen.add(key)
                selected.append(candidate)
                progressed = True
                break

            if len(selected) >= limit:
                break

        if not progressed:
            break

    ranking_queries = (
        [topic.strip()] if topic and topic.strip() else []
    ) + clean_queries

    async def collect_one(
        selected_candidate: dict[str, str],
    ) -> tuple[dict[str, object] | None, str | None, str]:
        requested_url = selected_candidate["url"]

        try:
            page = await fetch_page(requested_url)

        except SecurityError as exc:
            return None, f"{requested_url}: blocked_url ({exc})", requested_url

        except FetchError as exc:
            return None, _gap_for_fetch_error(requested_url, exc), requested_url

        if not page.text_sufficient:
            return (
                None,
                f"{requested_url}: too little extractable text (likely JS-rendered or intentionally short)",
                requested_url,
            )

        passages = select_excerpts(page.text, ranking_queries)
        excerpts: list[dict[str, object]] = []
        content_hash = sha256(page.text.encode("utf-8")).hexdigest()
        for passage in passages:
            excerpt: dict[str, object] = dict(passage)
            excerpt["expand"] = _fetch_action(
                page.url,
                passage["start_char"],
                min(EXPAND_CHARS, MAX_FETCH_CHARS),
                content_hash,
            )
            excerpts.append(excerpt)

        return (
            {
                "title": truncate_metadata(
                    page.title or selected_candidate["title"], MAX_TITLE_CHARS
                ),
                "url": page.url,
                "snippet": truncate_metadata(
                    selected_candidate["snippet"], MAX_SNIPPET_CHARS
                ),
                "source_type": classify_source_type(page.url),
                "excerpts": excerpts,
                "source_id": _source_id(page.url),
                "text_truncated": page.text_truncated,
                "content_hash": content_hash,
            },
            None,
            requested_url,
        )

    outcomes = await asyncio.gather(*(collect_one(candidate) for candidate in selected))

    sources: list[dict[str, object]] = []
    final_sources: dict[str, str] = {}

    for source, gap, candidate_url in outcomes:
        if gap is not None:
            gaps.append(gap)
            continue

        if source is None:
            continue

        final_key = normalize_url(str(source.get("url") or ""))

        kept_id = final_sources.get(final_key)

        if kept_id is not None:
            # Report the original candidate URL rather than merely repeating
            # the final URL shared by both candidates.
            gaps.append(
                f"{candidate_url}: resolves to same final document as {kept_id}"
            )
            continue

        final_sources[final_key] = str(source.get("source_id"))

        sources.append(source)
        if source["text_truncated"]:
            gaps.append(f"{source['url']}: extracted text truncated by character limit")

    bounded_gaps = [truncate_metadata(gap, MAX_GAP_CHARS) for gap in gaps]
    return CollectResponse.model_validate(
        {"query_variants": clean_queries, "sources": sources, "gaps": bounded_gaps}
    )
