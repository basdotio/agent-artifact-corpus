"""Web search for the agent: Brave Search API when a key is set, DuckDuckGo HTML otherwise."""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import httpx

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
DDG_URL = "https://html.duckduckgo.com/html/"
_RESULT = re.compile(
    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
    r'(?:<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(?P<snippet>.*?)</a>|<div[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(?P<snippet2>.*?)</div>)',
    re.S,
)
_TAGS = re.compile(r"<[^>]+>")


def _clean(fragment: str | None) -> str:
    return html.unescape(_TAGS.sub("", fragment or "")).strip()


def _real_url(href: str) -> str:
    """DuckDuckGo wraps result links in a redirect; unwrap the ``uddg`` target."""
    parsed = urlparse(href if href.startswith("http") else "https:" + href)
    target = parse_qs(parsed.query).get("uddg")
    return unquote(target[0]) if target else href


def parse_ddg_html(page: str, limit: int = 5) -> list[dict[str, str]]:
    results = []
    for m in _RESULT.finditer(page):
        results.append(
            {
                "title": _clean(m.group("title")),
                "url": _real_url(html.unescape(m.group("href"))),
                "snippet": _clean(m.group("snippet") or m.group("snippet2")),
            }
        )
        if len(results) >= limit:
            break
    return results


def parse_brave_json(data: dict[str, Any], limit: int = 5) -> list[dict[str, str]]:
    items = (data.get("web") or {}).get("results") or []
    return [
        {
            "title": _clean(i.get("title")),
            "url": str(i.get("url", "")),
            "snippet": _clean(i.get("description")),
        }
        for i in items[:limit]
    ]


class SearchError(RuntimeError):
    """The engine answered but gave no usable results (throttled, blocked or nothing found)."""


def _non_empty(engine: str, results: list[dict[str, str]]) -> list[dict[str, str]]:
    if not results:
        raise SearchError(
            f"{engine} returned no results (throttled or blocked, or nothing matched)"
        )
    return results


async def search(
    query: str,
    limit: int = 5,
    brave_key: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Return (engine, results). Raises httpx.HTTPError when the engine is unreachable."""
    owns = client is None
    client = client or httpx.AsyncClient(timeout=15.0, follow_redirects=True)
    try:
        if brave_key:
            resp = await client.get(
                BRAVE_URL,
                params={"q": query, "count": limit},
                headers={"X-Subscription-Token": brave_key, "Accept": "application/json"},
            )
            resp.raise_for_status()
            return "brave", _non_empty("brave", parse_brave_json(resp.json(), limit))
        resp = await client.post(
            DDG_URL, data={"q": query}, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
        )
        resp.raise_for_status()
        return "duckduckgo", _non_empty("duckduckgo", parse_ddg_html(resp.text, limit))
    finally:
        if owns:
            await client.aclose()


TAVILY_URL = "https://api.tavily.com/search"


async def tavily_search(
    query: str, limit: int, topic: str, api_key: str, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """Tavily (AURA's provider): a synthesized answer plus ranked source snippets."""
    body = {
        "query": query,
        "max_results": limit,
        "topic": "news" if topic == "news" else "general",
        "include_answer": True,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    own = client is None
    client = client or httpx.AsyncClient(timeout=20)
    try:
        resp = await client.post(TAVILY_URL, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if own:
            await client.aclose()
    results = [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in data.get("results") or []
    ][:limit]
    if not results and not data.get("answer"):
        raise SearchError("tavily returned nothing")
    return {"engine": "tavily", "answer": data.get("answer") or "", "results": results}
