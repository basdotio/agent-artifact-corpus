"""Local MCP server exposing a small DuckDuckGo web-search tool."""
from __future__ import annotations

import json

from ddgs import DDGS
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("research-search-tools")


@mcp.tool()
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web and return result titles, snippets, and source URLs."""
    query = query.strip()
    if not query:
        return json.dumps({"results": [], "error": "Query must not be empty."})

    max_results = max(1, min(int(max_results), 8))
    try:
        raw_results = DDGS().text(query, max_results=max_results)
        results = []
        for item in raw_results:
            results.append({
                "title": item.get("title", ""),
                "body": item.get("body", ""),
                "url": item.get("href", ""),
            })
        return json.dumps({"results": results}, ensure_ascii=False)
    except Exception as exc:
        # Return a short error message; avoid leaking local environment details.
        return json.dumps({
            "results": [],
            "error": f"Search failed ({type(exc).__name__}). Check network access and retry.",
        })


if __name__ == "__main__":
    mcp.run(transport="stdio")
