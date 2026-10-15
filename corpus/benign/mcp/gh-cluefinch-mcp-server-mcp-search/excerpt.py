"""BM25 excerpt selection + deterministic source_type classifier.

Excerpt offsets are character positions in the full extracted text — the
same coordinate system as web_fetch pagination. Every returned excerpt is a
literal slice of that text:

    excerpt["text"] == text[excerpt["start_char"]:excerpt["end_char"]]

That invariant lets the agent expand an excerpt with
web_fetch(url, start_offset=excerpt["start_char"]) without coordinate drift.

``source_type`` classifies source CATEGORY (official/academic/news/blog),
not factual reliability. ``unknown`` is the honest default for unrecognized
or malformed URLs. Domain classification uses exact-domain, subdomain, and
explicitly configured domain-suffix matching; substring heuristics are
deliberately not used.

Deterministic throughout: BM25 ranking uses paragraph order as the stable
tie-break. If no candidate has a positive BM25 score, leading eligible
paragraphs are returned instead.

Known limit (v1): no lemmatization; inflected word forms are not normalized.
CJK text uses deterministic overlapping bigrams rather than language-specific
word segmentation.
"""

import re
from typing import Final, TypedDict
from urllib.parse import urlsplit

from rank_bm25 import BM25Plus

from mcp_search.metadata_limits import MAX_HEADING_CHARS, truncate_metadata

MAX_EXCERPTS: Final = 3
EXCERPT_CHARS: Final = 500
MIN_PARAGRAPH_CHARS: Final = 40


class ExcerptData(TypedDict):
    """Literal passage and its coordinates before navigation is attached."""

    text: str
    start_char: int
    end_char: int
    heading: str | None
    truncated: bool


_WORD_RE = re.compile(r"[\w'-]+", re.UNICODE)
_CJK_RANGES: Final = (
    (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0x3040, 0x309F),  # Hiragana
    (0x30A0, 0x30FF),  # Katakana
    (0x1100, 0x11FF),  # Hangul Jamo
    (0x3130, 0x318F),  # Hangul Compatibility Jamo
    (0xAC00, 0xD7AF),  # Hangul Syllables
)
_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
_BLOCK_SEPARATOR_RE = re.compile(r"\r?\n[ \t]*\r?\n+")


def _is_cjk_char(char: str) -> bool:
    codepoint = ord(char)
    return any(start <= codepoint <= end for start, end in _CJK_RANGES)


def _tokenize(text: str) -> list[str]:
    """Tokenize words normally and CJK runs into overlapping bigrams."""
    result: list[str] = []

    for raw_token in _WORD_RE.findall(text):
        token = raw_token.lower()
        start = 0

        while start < len(token):
            cjk = _is_cjk_char(token[start])
            end = start + 1
            while end < len(token) and _is_cjk_char(token[end]) == cjk:
                end += 1

            run = token[start:end]
            if cjk and len(run) > 1:
                result.extend(run[index : index + 2] for index in range(len(run) - 1))
            else:
                result.append(run)

            start = end

    return result


def _block_spans(text: str) -> list[tuple[int, int]]:
    """Return spans of blank-line-separated blocks in the original text."""
    spans: list[tuple[int, int]] = []
    start = 0

    for match in _BLOCK_SEPARATOR_RE.finditer(text):
        spans.append((start, match.start()))
        start = match.end()

    if start < len(text):
        spans.append((start, len(text)))

    return spans


def _trimmed_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Trim surrounding whitespace while preserving original coordinates."""
    raw = text[start:end]

    left_trim = len(raw) - len(raw.lstrip())
    right_trim = len(raw) - len(raw.rstrip())

    trimmed_start = start + left_trim
    trimmed_end = end - right_trim

    if trimmed_end < trimmed_start:
        trimmed_end = trimmed_start

    return trimmed_start, trimmed_end


def _excerpt_end(block: str, limit: int) -> tuple[int, bool]:
    """Return an exact slice end and whether the block was truncated.

    Prefer the last whitespace boundary in the second half of the requested
    window. Otherwise use the hard character limit. The returned offset is
    always relative to ``block`` and never includes synthetic punctuation.
    """
    if len(block) <= limit:
        return len(block), False

    candidate = block[:limit]
    boundary = -1

    for index in range(len(candidate) - 1, -1, -1):
        if candidate[index].isspace():
            boundary = index
            break

    if boundary > limit // 2:
        end = boundary
    else:
        end = limit

    while end > 0 and block[end - 1].isspace():
        end -= 1

    return end, True


def select_excerpts(
    text: str,
    queries: list[str],
    max_excerpts: int = MAX_EXCERPTS,
    excerpt_chars: int = EXCERPT_CHARS,
) -> list[ExcerptData]:
    """Pick the most query-relevant passages.

    Returns dictionaries with:
        text: Literal slice from the original extracted text.
        start_char: Inclusive offset of that slice.
        end_char: Exclusive offset of that slice.
        heading: Nearest preceding Markdown heading, or None.
        truncated: Whether the source block continued after end_char.

    Candidate blocks shorter than MIN_PARAGRAPH_CHARS are ignored. Markdown
    heading-only blocks update heading context but are not themselves excerpt
    candidates.

    Ranking is deterministic BM25. Only positive-score candidates are returned
    when any positive matches exist; zero-score candidates are not used merely
    to fill the quota. If no candidate has a positive score, the first eligible
    blocks are returned in document order.
    """
    if max_excerpts <= 0 or excerpt_chars <= 0:
        return []

    candidates: list[tuple[int, int, str | None, bool]] = []

    current_heading: str | None = None

    for block_start, block_end in _block_spans(text):
        start, end = _trimmed_span(text, block_start, block_end)

        if start >= end:
            continue

        block = text[start:end]

        heading_match = _HEADING_RE.fullmatch(block)

        if heading_match is not None:
            current_heading = truncate_metadata(
                heading_match.group(2).strip(), MAX_HEADING_CHARS
            )
            continue

        if len(block) < MIN_PARAGRAPH_CHARS:
            continue

        # Rank bounded passages so matching terms cannot disappear beyond
        # the leading characters returned from a very long paragraph.
        while start < end:
            length, _ = _excerpt_end(text[start:end], excerpt_chars)
            window_end = start + length
            if window_end == start:
                break
            candidates.append((start, window_end, current_heading, window_end < end))
            start = window_end
            while start < end and text[start].isspace():
                start += 1

    if not candidates:
        return []

    query_tokens = _tokenize(" ".join(queries))

    order = list(range(len(candidates)))

    if query_tokens:
        corpus = [
            _tokenize(text[start:end])
            for start, end, _heading, _continued in candidates
        ]

        if any(corpus):
            # Positive IDF avoids zero/negative relevance on tiny documents.
            # delta=0 keeps passages with no matching tokens at score zero.
            bm25 = BM25Plus(corpus, delta=0)
            scores = bm25.get_scores(query_tokens)

            ranked = sorted(
                (index for index in range(len(candidates)) if scores[index] > 0),
                key=lambda index: (-scores[index], index),
            )

            if ranked:
                order = ranked

    result: list[ExcerptData] = []

    for index in order[:max_excerpts]:
        start, block_end, heading, continued = candidates[index]
        block = text[start:block_end]

        relative_end, truncated = _excerpt_end(block, excerpt_chars)

        end = start + relative_end

        result.append(
            {
                "text": text[start:end],
                "start_char": start,
                "end_char": end,
                "heading": heading,
                "truncated": truncated or continued,
            }
        )

    return result


def _matches(
    host: str, domains: frozenset[str], suffixes: tuple[str, ...] = ()
) -> bool:
    """Match an exact domain, its subdomains, or configured domain suffixes."""
    if host in domains:
        return True

    if any(host.endswith("." + domain) for domain in domains):
        return True

    return any(host.endswith(suffix) for suffix in suffixes)


# Government and intergovernmental sources.
_OFFICIAL_SUFFIXES: Final = (".gov", ".mil", ".gov.uk", ".int", ".europa.eu")

_OFFICIAL_DOMAINS: Final = frozenset(
    {"europa.eu", "un.org", "imf.org", "worldbank.org"}
)

# Government-hosted services whose source category is more useful to the
# research agent as academic/scholarly than as generic official material.
_ACADEMIC_EXCEPTION_HOSTS: Final = frozenset({"pubmed.ncbi.nlm.nih.gov"})

# Academia, scholarly indexes, societies, and major scholarly publishers.
_ACADEMIC_SUFFIXES: Final = (".edu", ".ac.uk")

_ACADEMIC_DOMAINS: Final = frozenset(
    {
        "arxiv.org",
        "doi.org",
        "semanticscholar.org",
        "acm.org",
        "ieee.org",
        "elsevier.com",
        "sciencedirect.com",
        "springer.com",
        "nature.com",
        "science.org",
        "plos.org",
        "mdpi.com",
        "tandfonline.com",
        "wiley.com",
        "cambridge.org",
        "oup.com",
    }
)

_NEWS_DOMAINS: Final = frozenset(
    {
        "reuters.com",
        "apnews.com",
        "bbc.com",
        "bbc.co.uk",
        "nytimes.com",
        "washingtonpost.com",
        "theguardian.com",
        "cnn.com",
        "ft.com",
        "bloomberg.com",
        "economist.com",
        "wsj.com",
        "theatlantic.com",
        "foreignaffairs.com",
    }
)

_BLOG_DOMAINS: Final = frozenset(
    {
        "medium.com",
        "substack.com",
        "dev.to",
        "hashnode.dev",
        "wordpress.com",
        "blogger.com",
        "tumblr.com",
        "ghost.io",
    }
)


def classify_source_type(url: str) -> str:
    """Classify a URL as official | academic | news | blog | unknown.

    This is a deterministic source-category hint, not a reliability score.
    Matching uses exact domains, subdomains of listed domains, or explicitly
    configured domain suffixes. Unrecognized and malformed URLs return
    ``unknown``.
    """
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
    except ValueError:
        return "unknown"

    host = (hostname or "").lower().rstrip(".")

    if not host:
        return "unknown"

    if _matches(host, _ACADEMIC_EXCEPTION_HOSTS):
        return "academic"

    if _matches(host, _OFFICIAL_DOMAINS, _OFFICIAL_SUFFIXES):
        return "official"

    if _matches(host, _ACADEMIC_DOMAINS, _ACADEMIC_SUFFIXES):
        return "academic"

    if _matches(host, _NEWS_DOMAINS):
        return "news"

    if _matches(host, _BLOG_DOMAINS):
        return "blog"

    return "unknown"
