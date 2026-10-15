"""Validated public response contracts shared by MCP schemas and runtime output.

RootModel preserves the existing flat JSON on the wire while describing both
success and error branches. Every field is required; nullable means unavailable,
not omitted. No inferred credibility or relevance scores are exposed.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from mcp_search.metadata_limits import (
    MAX_ENGINE_CHARS,
    MAX_ENGINE_NAME_CHARS,
    MAX_ERROR_CHARS,
    MAX_GAP_CHARS,
    MAX_HEADING_CHARS,
    MAX_HINT_CHARS,
    MAX_SNIPPET_CHARS,
    MAX_TITLE_CHARS,
    MAX_UNRESPONSIVE_ENGINES,
)
from mcp_search.navigation import (
    MAX_LINK_LABEL_CHARS,
    MAX_LINKS_PER_RESPONSE,
    MAX_REL_TOKEN_CHARS,
    MAX_REL_TOKENS,
    MAX_RETAINED_LINKS,
    MAX_URL_CHARS,
)

CONTENT_HASH_PATTERN = r"^[0-9a-f]{64}$"

SourceType = Annotated[
    Literal["official", "academic", "news", "blog", "unknown"],
    Field(
        description="Domain-based source category, not credibility or factual reliability."
    ),
]
ContentHash = Annotated[
    str,
    Field(
        pattern=CONTENT_HASH_PATTERN,
        description="SHA-256 of the entire retained extracted text, not this slice. Ready actions include it as expected_content_hash for server-side checking. Does not establish origin freshness, cache status or factual reliability.",
    ),
]
ExpectedContentHash = Annotated[
    str,
    Field(
        pattern=CONTENT_HASH_PATTERN,
        description="Expected retained-text SHA-256. The server returns content_changed without a slice on mismatch. Ready continuation/expand arguments supply this value; keep it when adjusting the reading budget.",
    ),
]
LinksHash = Annotated[
    str,
    Field(
        pattern=CONTENT_HASH_PATTERN,
        description="SHA-256 version identifier for the entire retained ordered link list before filtering or pagination. It does not establish origin freshness or approve destinations for fetching.",
    ),
]
ExpectedLinksHash = Annotated[
    str,
    Field(
        pattern=CONTENT_HASH_PATTERN,
        description="Expected retained-link-list version. A mismatch returns links_changed without applying the old list index.",
    ),
]
TextTruncated = Annotated[
    bool,
    Field(
        description="True when extraction exceeded the server's retained-text limit. The omitted tail cannot be read with pagination. Independent of slice/excerpt truncated."
    ),
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ToolError(Contract):
    """Expected failure: inspect error and hint instead of success fields."""

    error: str = Field(
        max_length=MAX_ERROR_CHARS,
        description="Operational or argument error. blocked_url means the URL was rejected by the outbound security policy.",
    )
    hint: str = Field(
        max_length=MAX_HINT_CHARS,
        description="Suggested recovery action or details; may be empty. No successful content is implied.",
    )


class ContentChangedError(Contract):
    """The retained text differs from the expected version; no slice is returned."""

    error: Literal["content_changed"] = Field(
        description="Old coordinates were not used. Reacquire the source material and select coordinates again; this does not establish that the old citation was false."
    )
    hint: str = Field(
        max_length=MAX_HINT_CHARS,
        description="Suggested recovery action or details; may be empty. No successful content is implied.",
    )


class LinksChangedError(Contract):
    """The retained navigation list differs from the expected version."""

    error: Literal["links_changed"] = Field(
        description="The old link-list index was not used. Reacquire navigation without the old hash before continuing."
    )
    hint: str = Field(
        max_length=MAX_HINT_CHARS,
        description="Suggested recovery action or details; may be empty.",
    )


class WebFetchArguments(Contract):
    """Copy these arguments to this server's web_fetch without joining source fields."""

    url: str = Field(
        description="Final fetched URL; normal URL validation still applies on execution."
    )
    start_offset: int = Field(
        ge=0,
        description="Server-computed Unicode-character offset; do not convert to byte or UTF-16 offsets.",
    )
    max_chars: int = Field(
        ge=1,
        description="Explicit reading budget, bounded by the server cap. May be adjusted while retaining expected_content_hash.",
    )
    expected_content_hash: ExpectedContentHash


class FetchAction(Contract):
    """Optional reading action, not a command to execute automatically."""

    tool: Literal["web_fetch"] = Field(
        description="Tool name within this MCP server; use the client's corresponding qualified name if needed."
    )
    arguments: WebFetchArguments = Field(
        description="Ready-to-use input arguments, including retained-text version checking."
    )


class WebLinksArguments(Contract):
    """Copy these arguments to this server's web_links."""

    url: str = Field(
        max_length=MAX_URL_CHARS,
        description="Final fetched page URL; normal URL validation still applies when the action executes.",
    )
    same_origin: bool | None = Field(
        description="Optional origin filter preserved across continuation: true keeps same-origin links, false keeps cross-origin links, null keeps both."
    )
    start_index: int = Field(
        ge=0,
        description="Zero-based index in the retained link list after applying same_origin filtering.",
    )
    max_links: int = Field(
        ge=1,
        le=MAX_LINKS_PER_RESPONSE,
        description="Maximum number of retained links returned in this page.",
    )
    expected_links_hash: ExpectedLinksHash


class LinkAction(Contract):
    """Optional version-checked continuation for web_links."""

    tool: Literal["web_links"] = Field(
        description="Tool name within this MCP server; use the client's corresponding qualified name if needed."
    )
    arguments: WebLinksArguments = Field(
        description="Ready-to-use link continuation arguments, including retained-list version checking."
    )


class DiscoveredLink(Contract):
    """One locally parsed navigation address; fetching it still requires SSRF validation."""

    label: str = Field(
        max_length=MAX_LINK_LABEL_CHARS,
        description="Bounded best-effort label derived from anchor text, aria-label, title or image alt; not guaranteed literal visible text.",
    )
    url: str = Field(
        max_length=MAX_URL_CHARS,
        description="Resolved HTTP(S) navigation URL including fragment. It has not been fetched, DNS-resolved, or approved for retrieval; selecting it later invokes the normal outbound safety policy.",
    )
    same_origin: bool = Field(
        description="Technical origin comparison: true only when scheme, normalized hostname and effective port match the final fetched page URL. This is not a same-organization or trust judgment."
    )
    same_document: bool = Field(
        description="Whether the link has the same document identity as the final page after ignoring only the fragment. This does not map the fragment to extracted-text coordinates."
    )
    fragment: str | None = Field(
        description="URL fragment without the leading #, or null when absent."
    )
    rel: list[Annotated[str, Field(max_length=MAX_REL_TOKEN_CHARS)]] = Field(
        max_length=MAX_REL_TOKENS,
        description="Bounded unique rel tokens merged across duplicate anchors for this retained URL.",
    )


class LinksSuccess(Contract):
    """One page of retained navigation links from a fetched HTML document."""

    url: str = Field(
        max_length=MAX_URL_CHARS, description="Final fetched URL after redirects."
    )
    links_hash: LinksHash
    links: list[DiscoveredLink] = Field(
        max_length=MAX_LINKS_PER_RESPONSE,
        description="Navigation choices from this page after optional origin filtering and pagination, in document order. These destinations were parsed but not fetched or DNS-approved.",
    )
    total_retained_matching: int = Field(
        ge=0,
        le=MAX_RETAINED_LINKS,
        description="Number of retained links matching the current origin filter. This is not the total number of anchors in the original HTML when links_truncated is true.",
    )
    next_start_index: int | None = Field(
        ge=0,
        description="Next index in the filtered retained list, or null when the retained list is exhausted.",
    )
    links_truncated: bool = Field(
        description="True when otherwise admissible navigation data was dropped by page-level scan/count/byte/URL limits. Independent of continuation."
    )
    cache_hit: bool = Field(
        description="Whether the shared processed page came from the process-local fetch cache."
    )
    continuation: LinkAction | None = Field(
        description="Ready next-page navigation action. Call its tool with its arguments when more retained links are useful. Null means the retained list is exhausted; links_truncated may still mean some original links were never retained."
    )


class SearchResult(Contract):
    title: str = Field(
        max_length=MAX_TITLE_CHARS,
        description="Title supplied by the search engine; may be empty.",
    )
    url: str = Field(
        description="Candidate URL. Pass to web_fetch for preview/reading, web_links for page navigation, or research_collect(urls=[...]) for excerpts. Not yet fetched or verified."
    )
    snippet: str = Field(
        max_length=MAX_SNIPPET_CHARS,
        description="Search-engine preview text, not a verified excerpt of a fetched document; may be empty.",
    )
    engine: str = Field(
        max_length=MAX_ENGINE_CHARS,
        description="Comma-separated contributing engine names; may be empty.",
    )
    source_type: SourceType


class SearchSuccess(Contract):
    """Search candidates, not fetched source documents."""

    results: list[SearchResult] = Field(
        description="Deduplicated candidates in upstream order, at most max_results after the configured cap. Empty does not prove absence of information."
    )
    unresponsive_engines: list[
        Annotated[str, Field(max_length=MAX_ENGINE_NAME_CHARS)]
    ] = Field(
        max_length=MAX_UNRESPONSIVE_ENGINES,
        description="Engines that failed to respond. Nonempty means coverage is incomplete, even when results are present.",
    )
    query_used: str = Field(
        description="Effective query including site: and -site: operators from domain/exclude_domains."
    )
    cached: bool = Field(
        description="Whether this search response came from the process-local TTL cache."
    )


class FetchSuccess(Contract):
    """One slice of a fetched HTML document's retained Markdown text."""

    title: str = Field(
        max_length=MAX_TITLE_CHARS,
        description="Extracted page title; empty if unavailable.",
    )
    url: str = Field(
        description="Final fetched URL after redirects. Use for further reading. Not an HTML rel=canonical declaration."
    )
    content: str = Field(
        description="Markdown slice beginning at start_offset (clamped at end of text), bounded by max_chars. max_chars=500 gives a short preview. Empty when the offset is at or beyond the retained text end."
    )
    total_chars: int = Field(
        ge=0,
        description="Length of the entire retained extracted text in Unicode characters, not bytes or length of this slice.",
    )
    next_start: int | None = Field(
        ge=0,
        description="Pass as web_fetch(start_offset=next_start) to continue without overlap. Null means the retained text has ended.",
    )
    truncated: bool = Field(
        description="True when more retained text follows this slice; continue at next_start. Does not mean that the document itself was cut by the server limit."
    )
    cache_hit: bool = Field(
        description="Whether the extracted document came from the process-local TTL cache."
    )
    source_type: SourceType
    text_truncated: TextTruncated
    content_hash: ContentHash
    continuation: FetchAction | None = Field(
        description="Optional next read: call the indicated tool with these arguments. Preserves the effective slice budget and checks the text version. Null at the retained-text end, even when text_truncated is true."
    )


class Excerpt(Contract):
    text: str = Field(
        description="Literal slice of the retained document: text[start_char:end_char]. BM25 selection or leading-text fallback; not a summary or a reliability assessment."
    )
    start_char: int = Field(
        ge=0,
        description="Inclusive Unicode-character offset for citations or manual reading. Use expand for a ready version-checked call.",
    )
    end_char: int = Field(
        ge=0,
        description="Exclusive offset in the same text. end_char - start_char equals the excerpt text length.",
    )
    heading: Annotated[str, Field(max_length=MAX_HEADING_CHARS)] | None = Field(
        description="Nearest preceding extracted Markdown heading, or null if unavailable. This is local heading context, not a page outline."
    )
    truncated: bool = Field(
        description="True when the original paragraph continues beyond end_char. web_fetch can read surrounding text; not a relevance score."
    )
    expand: FetchAction = Field(
        description="Optional read starting at this excerpt, with the source URL, explicit budget and expected hash already supplied. Execute only if more context is useful."
    )


class ResearchSource(Contract):
    title: str = Field(
        max_length=MAX_TITLE_CHARS,
        description="Extracted title, falling back to search title; may be empty.",
    )
    url: str = Field(
        description="Final fetched URL. Pass to web_fetch together with an excerpt's start_char to expand that excerpt."
    )
    snippet: str = Field(
        max_length=MAX_SNIPPET_CHARS,
        description="Search-engine snippet; empty for explicit URLs. Separate from verified literal excerpts.",
    )
    source_type: SourceType
    excerpts: list[Excerpt] = Field(
        description="Bounded passages selected by BM25 against topic and queries; leading eligible text when no tokens match. May be empty. The agent evaluates relevance."
    )
    source_id: str = Field(
        pattern=r"^src_[0-9a-f]{16}$",
        description="Stable ID derived from normalized final URL, for citations across calls. Identifies the URL, not a fixed document version; content_hash identifies the retained text.",
    )
    text_truncated: TextTruncated
    content_hash: ContentHash


class CollectSuccess(Contract):
    """Collected raw material and explicit coverage gaps; no synthesis."""

    query_variants: list[str] = Field(
        description="Agent-supplied queries after whitespace cleanup. Empty in URL-only mode; the server never invents queries."
    )
    sources: list[ResearchSource] = Field(
        description="Successfully fetched sources, deduplicated by final URL. max_sources limits attempted candidates, not guaranteed successful sources. Explicit URLs take priority, then query pools are interleaved."
    )
    gaps: list[Annotated[str, Field(max_length=MAX_GAP_CHARS)]] = Field(
        description="Collection limitations: search failures/empty results, unresponsive engines, blocked or unavailable pages, insufficient text, redirect duplicates, omitted URLs and truncated documents. These are collection facts, not conclusions about the research topic."
    )


class ToolResponse(RootModel):
    # Concrete responses declare their own payload; all union branches are objects.
    # MCP requires type: object at the schema root.
    model_config = ConfigDict(json_schema_extra={"type": "object"})


class SearchResponse(ToolResponse):
    """Either SearchSuccess or ToolError, with fields directly at the root."""

    root: SearchSuccess | ToolError


class FetchResponse(ToolResponse):
    """A slice, a content_changed failure, or another error; fields stay at the root."""

    root: FetchSuccess | ContentChangedError | ToolError


class LinksResponse(ToolResponse):
    """A link page, a links_changed failure, or another expected error."""

    root: LinksSuccess | LinksChangedError | ToolError


class CollectResponse(ToolResponse):
    """Either CollectSuccess or ToolError, with fields directly at the root."""

    root: CollectSuccess | ToolError
