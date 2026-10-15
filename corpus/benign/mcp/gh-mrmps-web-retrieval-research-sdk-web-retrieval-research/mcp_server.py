"""Stdio MCP tools with provider-native request bodies and complete responses."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import ResearchClient


mcp = FastMCP("web-retrieval-research")


def _call(provider: str, operation: str, request: dict[str, Any]) -> dict[str, Any]:
    with ResearchClient() as client:
        return client.call(provider, operation, request).to_dict()


@mcp.tool()
def context_search(request: dict[str, Any]) -> dict[str, Any]:
    """POST Context /v1/web/search. Pass native fields such as query, numResults, highlightsOptions, and markdownOptions. Search result freshness and fetched-page freshness differ; inspect the raw result."""
    return _call("context", "search", request)


@mcp.tool()
def context_scrape(request: dict[str, Any]) -> dict[str, Any]:
    """POST Context /v1/web/scrape. Use formats.markdown or formats.highlights with highlightsParams.query. maxAgeMs defaults to 3 days; 0 requests fresh outputs. Check each format's success and cache_metadata."""
    return _call("context", "scrape", request)


@mcp.tool()
def exa_search(request: dict[str, Any]) -> dict[str, Any]:
    """POST Exa /search. Pass query and optional contents.highlights or contents.text. Search index freshness differs from page content; preserve result statuses and cache source."""
    return _call("exa", "search", request)


@mcp.tool()
def exa_contents(request: dict[str, Any]) -> dict[str, Any]:
    """POST Exa /contents for known URLs. Use highlights.query or text; maxAgeHours=0 requests fresh crawl, -1 only cached, omitted uses Exa defaults. Check per-URL statuses."""
    return _call("exa", "contents", request)


@mcp.tool()
def firecrawl_search(request: dict[str, Any]) -> dict[str, Any]:
    """POST Firecrawl /v2/search. Pass query and optional highlights/scrapeOptions. Search discovery is distinct from scraping and has separate provider controls."""
    return _call("firecrawl", "search", request)


@mcp.tool()
def firecrawl_scrape(request: dict[str, Any]) -> dict[str, Any]:
    """POST Firecrawl /v2/scrape. Use formats=['markdown'] or a highlights format object. maxAge is milliseconds, defaults to 2 days; 0 requests a new scrape. Check success and page metadata."""
    return _call("firecrawl", "scrape", request)


@mcp.tool()
def parallel_search(request: dict[str, Any]) -> dict[str, Any]:
    """POST Parallel /v1/search. Pass native search_queries/objective and keep raw ranked results. This searches Parallel's index; it is not a live fetch guarantee."""
    return _call("parallel", "search", request)


@mcp.tool()
def parallel_extract(request: dict[str, Any]) -> dict[str, Any]:
    """POST Parallel /v1/extract. Pass urls/objective and advanced_settings.fetch_policy. max_age_seconds has a 600-second minimum; disable_cache_fallback fails if live fetch fails. Excerpts and full_content are different outputs."""
    return _call("parallel", "extract", request)


def main() -> None:
    mcp.run(transport="stdio")
