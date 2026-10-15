"""Bounded extraction and versioning of navigable HTML links.

Link discovery is deliberately local: parsing a returned link never resolves its
hostname or approves it for fetching. A later retrieval applies the normal
outbound SSRF policy to the selected URL.
"""

import json
import re
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Final
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup
from bs4.element import Comment, NavigableString, Tag

from mcp_search.security import SecurityError, normalize_hostname
from mcp_search.url_limits import MAX_URL_CHARS as MAX_URL_CHARS
from mcp_search.url_limits import exceeds_url_limit

MAX_RETAINED_LINKS: Final = 512
DEFAULT_LINKS_PER_RESPONSE: Final = 50
MAX_LINKS_PER_RESPONSE: Final = 100
MAX_LINK_LABEL_CHARS: Final = 512
MAX_REL_TOKENS: Final = 16
MAX_REL_TOKEN_CHARS: Final = 64
MAX_NAVIGATION_BYTES: Final = 128 * 1024
MAX_LINK_ELEMENTS_SCANNED: Final = 4096

_EXCLUDED_LABEL_ANCESTORS: Final = frozenset(
    {"script", "style", "noscript", "template"}
)
_LINKS_HASH_DOMAIN: Final = b"cluefinch-links-v1\0"
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class PageLink:
    """One retained navigation address after deterministic deduplication."""

    label: str
    url: str
    same_origin: bool
    same_document: bool
    fragment: str | None
    rel: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NavigationResult:
    """Bounded navigation data retained for one fetched HTML document."""

    links: tuple[PageLink, ...]
    links_truncated: bool


def _bounded_text(value: str, limit: int) -> str:
    value = _WHITESPACE_RE.sub(" ", value).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…" if limit > 1 else "…"


def _canonical_http_url(url: str, *, keep_fragment: bool) -> str | None:
    """Return a conservative HTTP(S) navigation identity without network I/O."""
    if any(ord(char) < 32 or ord(char) == 127 for char in url) or "\\" in url:
        return None
    try:
        parts = urlsplit(url)
        hostname = parts.hostname
        port = parts.port
    except ValueError:
        return None

    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        return None
    if parts.username is not None or parts.password is not None:
        return None

    host = (hostname or "").rstrip(".")
    if not host or "%" in host:
        return None
    try:
        host = normalize_hostname(host)
    except SecurityError:
        return None

    host_part = f"[{host}]" if ":" in host else host
    netloc = host_part
    if port is not None and (scheme, port) not in {("http", 80), ("https", 443)}:
        netloc = f"{host_part}:{port}"

    canonical = urlunsplit(
        (
            scheme,
            netloc,
            parts.path or "/",
            parts.query,
            parts.fragment if keep_fragment else "",
        )
    )
    # Use HTTPX's spelling for Unicode components without decoding escapes or
    # rebuilding query parameters. Fragments remain part of link identity.
    try:
        return str(httpx.URL(canonical))
    except (httpx.InvalidURL, UnicodeError):
        return None


def _origin(url: str) -> tuple[str, str, int] | None:
    try:
        parts = urlsplit(url)
        host = normalize_hostname((parts.hostname or "").rstrip("."))
        port = parts.port
    except (ValueError, UnicodeError):
        return None
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not host:
        return None

    if port is None:
        port = 443 if scheme == "https" else 80

    return scheme, host, port


def _label(anchor: Tag) -> str:
    text_parts: list[str] = []
    for descendant in anchor.descendants:
        if not isinstance(descendant, NavigableString) or isinstance(
            descendant, Comment
        ):
            continue
        parent = descendant.parent
        if isinstance(parent, Tag) and parent.name in _EXCLUDED_LABEL_ANCESTORS:
            continue
        text_parts.append(str(descendant))

    text = _bounded_text(" ".join(text_parts), MAX_LINK_LABEL_CHARS)
    if text:
        return text

    for attribute in ("aria-label", "title"):
        value = anchor.get(attribute)
        if isinstance(value, str):
            value = _bounded_text(value, MAX_LINK_LABEL_CHARS)
            if value:
                return value

    image = anchor.find("img")
    if isinstance(image, Tag):
        alt = image.get("alt")
        if isinstance(alt, str):
            alt = _bounded_text(alt, MAX_LINK_LABEL_CHARS)
            if alt:
                return alt
    return ""


def _rel(anchor: Tag) -> tuple[str, ...]:
    raw = anchor.get("rel")
    if isinstance(raw, str):
        tokens = raw.split()
    elif isinstance(raw, list):
        tokens = [str(item) for item in raw]
    else:
        tokens = []

    result: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized = _bounded_text(token, MAX_REL_TOKEN_CHARS)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
        if len(result) >= MAX_REL_TOKENS:
            break
    return tuple(result)


def link_payload(link: PageLink) -> dict[str, object]:
    """Return the fixed-order public representation used for hashing and output."""
    return {
        "label": link.label,
        "url": link.url,
        "same_origin": link.same_origin,
        "same_document": link.same_document,
        "fragment": link.fragment,
        "rel": list(link.rel),
    }


def _serialized_link_size(link: PageLink) -> int:
    return len(
        json.dumps(
            link_payload(link), ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    )


def links_hash(links: tuple[PageLink, ...]) -> str:
    """Version the entire retained ordered navigation list before filtering."""
    payload = json.dumps(
        [link_payload(link) for link in links],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(_LINKS_HASH_DOMAIN + payload).hexdigest()


def extract_navigation(html: str, final_url: str) -> NavigationResult:
    """Extract bounded <a href> navigation in document order."""
    soup = BeautifulSoup(html, "html.parser")
    # Exclude inactive subtrees before both label extraction and the scan ceiling.
    for element in soup.find_all(_EXCLUDED_LABEL_ANCESTORS):
        element.decompose()
    final_identity = _canonical_http_url(final_url, keep_fragment=False) or final_url
    final_origin = _origin(final_identity)

    base_url = final_identity
    base = soup.find("base", href=True)
    if isinstance(base, Tag):
        raw_base = base.get("href")
        if isinstance(raw_base, str):
            try:
                candidate = urljoin(final_identity, raw_base.strip())
            except ValueError:
                candidate = ""
            usable = _canonical_http_url(candidate, keep_fragment=False)
            if usable is not None:
                try:
                    if not exceeds_url_limit(usable):
                        base_url = usable
                except (httpx.InvalidURL, UnicodeError):
                    pass

    retained: list[PageLink] = []
    identities: dict[str, int] = {}
    sizes: list[int] = []
    total_bytes = 2
    truncated = False

    anchors = soup.find_all("a", href=True)
    if len(anchors) > MAX_LINK_ELEMENTS_SCANNED:
        truncated = True
        anchors = anchors[:MAX_LINK_ELEMENTS_SCANNED]

    for anchor in anchors:
        if not isinstance(anchor, Tag):
            continue
        raw_href = anchor.get("href")
        if not isinstance(raw_href, str):
            continue
        try:
            resolved = urljoin(base_url, raw_href.strip())
            scheme = urlsplit(resolved).scheme.lower()
        except ValueError:
            continue
        if scheme not in {"http", "https"}:
            continue
        try:
            if exceeds_url_limit(resolved):
                truncated = True
                continue
        except (httpx.InvalidURL, UnicodeError):
            continue

        canonical = _canonical_http_url(resolved, keep_fragment=True)
        if canonical is None:
            continue
        try:
            if exceeds_url_limit(canonical):
                truncated = True
                continue
        except (httpx.InvalidURL, UnicodeError):
            continue

        no_fragment = _canonical_http_url(canonical, keep_fragment=False)
        link = PageLink(
            label=_label(anchor),
            url=canonical,
            same_origin=final_origin is not None and _origin(canonical) == final_origin,
            same_document=no_fragment == final_identity,
            fragment=urlsplit(canonical).fragment or None,
            rel=_rel(anchor),
        )

        existing_index = identities.get(canonical)
        if existing_index is not None:
            existing = retained[existing_index]
            merged_rel = list(existing.rel)
            for token in link.rel:
                if token not in merged_rel and len(merged_rel) < MAX_REL_TOKENS:
                    merged_rel.append(token)
            merged = replace(
                existing, label=existing.label or link.label, rel=tuple(merged_rel)
            )
            old_size = sizes[existing_index]
            new_size = _serialized_link_size(merged)
            if total_bytes - old_size + new_size <= MAX_NAVIGATION_BYTES:
                retained[existing_index] = merged
                sizes[existing_index] = new_size
                total_bytes += new_size - old_size
            elif merged != existing:
                truncated = True
            continue

        if len(retained) >= MAX_RETAINED_LINKS:
            truncated = True
            continue

        size = _serialized_link_size(link)
        separator = 1 if retained else 0
        if total_bytes + separator + size > MAX_NAVIGATION_BYTES:
            truncated = True
            continue

        identities[canonical] = len(retained)
        retained.append(link)
        sizes.append(size)
        total_bytes += separator + size

    return NavigationResult(tuple(retained), truncated)
