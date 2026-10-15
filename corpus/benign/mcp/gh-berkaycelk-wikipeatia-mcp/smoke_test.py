#!/usr/bin/env python3
"""Smoke test: spawn the server over stdio and exercise a few tools.

Usage:
    uv run --with fastmcp --with httpx python smoke_test.py

Hits the live public APIs (wikipeatia.org, search.wikipeatia.org), so keep
it gentle: it makes only a handful of calls.
"""
import asyncio
import sys
from pathlib import Path

from fastmcp import Client

SERVER = Path(__file__).resolve().parent / "server.py"

EXPECTED_TOOLS = {
    "corpus_search", "corpus_semantic_search", "corpus_ask", "corpus_deep_ask",
    "corpus_topics", "corpus_get_doc", "wiki_read", "wiki_get_page",
    "raypeat_read_article",
}


async def run() -> int:
    failures: list[str] = []

    async with Client(SERVER) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        print(f"ok  connected over stdio; {len(names)} tools registered")

        missing = EXPECTED_TOOLS - names
        if missing:
            failures.append(f"missing tools: {sorted(missing)}")

        health = (await client.call_tool("corpus_health", {})).data
        print(f"ok  corpus_health: {health}")

        stats = (await client.call_tool("wiki_get_site_stats", {})).data
        print(f"ok  wiki: {stats.get('sitename')} / {stats.get('total_pages')} pages")

        hits = (await client.call_tool(
            "corpus_search", {"query": "PUFA", "limit": 3}
        )).data
        n = len(hits.get("results", []))
        print(f"ok  corpus_search('PUFA'): {n} results")
        if n == 0:
            failures.append("corpus_search returned 0 results")

        filt = (await client.call_tool(
            "corpus_search",
            {"query": "thyroid", "limit": 2, "doc_type": "interview",
             "series": "Ask the Herb Doctor"},
        )).data
        n2 = len(filt.get("results", []))
        print(f"ok  corpus_search with filters: {n2} results")
        if n2 == 0:
            failures.append("filtered corpus_search returned 0 results")

    if failures:
        print("\nFAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nsmoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
