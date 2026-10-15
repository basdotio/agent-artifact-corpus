"""FastMCP server exposing the toolkit's tools.

Run standalone:  python -m mcp_toolkit.server   (streamable HTTP on :8100)
The LangGraph agent in agent.py talks to these tools over MCP.
"""
from __future__ import annotations

import os

from fastmcp import FastMCP

from .tools_impl import doc_search_impl, record_lookup_impl, text_stats_impl


def create_server(data_dir: str | None = None) -> FastMCP:
    data_dir = data_dir or os.getenv("DATA_DIR", "data")
    server = FastMCP("mcp-agent-toolkit")

    @server.tool(description="Search bundled support documentation. Read-only.")
    def doc_search(query: str, k: int = 3) -> list[dict]:
        """Search the bundled knowledge base for relevant help articles."""
        return doc_search_impl(query, data_dir, k)

    @server.tool(description="Look up a bundled record by ID (e.g. R-2003). Read-only.")
    def record_lookup(record_id: str) -> dict | None:
        """Fetch a record's status and summary by its ID."""
        return record_lookup_impl(record_id, data_dir)

    @server.tool(description="Compute word/char counts, reading time and top keywords. Read-only.")
    def text_stats(text: str) -> dict:
        """Analyze a piece of text: counts, reading time, keywords."""
        return text_stats_impl(text)

    return server


mcp = create_server()

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8100")))
