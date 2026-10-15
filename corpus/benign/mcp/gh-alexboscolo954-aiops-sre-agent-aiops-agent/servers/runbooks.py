"""Runbooks MCP server: markdown runbooks with front matter mapping them to alerts.

    ---
    title: Pod crash looping
    alerts: [KubePodCrashLooping]
    ---
    ...steps...

ponytail: exact alertname match plus a keyword search. Good up to a few hundred
runbooks; swap in embeddings search if the collection grows past that.
"""

from pathlib import Path
from typing import Any

import yaml
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from aiops_agent.servers import Access

READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
ACCESS: dict[str, Access] = {
    "runbook_for_alert": "read",
    "search_runbooks": "read",
    "read_runbook": "read",
}  # ADR 0002


def load(directory: Path) -> dict[str, dict[str, Any]]:
    books = {}
    for path in sorted(directory.glob("*.md")):
        text = path.read_text()
        meta: dict[str, Any] = {}
        if text.startswith("---"):
            _, front, text = text.split("---", 2)
            meta = yaml.safe_load(front) or {}
        books[path.stem] = {
            "title": meta.get("title", path.stem),
            "alerts": meta.get("alerts", []),
            "body": text.strip(),
        }
    return books


def build_server(directories: list[Path]) -> FastMCP:
    """Later directories win on a name clash: a Contract's own Runbook overrides
    a shared one with the same name."""
    books: dict[str, dict[str, Any]] = {}
    for directory in directories:
        books |= load(directory)
    mcp = FastMCP("runbooks", instructions="Team runbooks for known alerts.")

    @mcp.tool(annotations=READ)
    def runbook_for_alert(alertname: str) -> dict[str, Any]:
        """Every runbook mapped to an alert name (one alert can map to several,
        e.g. a crash loop caused by OOM). Check this first, then pick the one
        that matches what you find."""
        matches = [
            {"name": name, "title": book["title"], "content": book["body"]}
            for name, book in books.items()
            if alertname in book["alerts"]
        ]
        if not matches:
            return {
                "runbooks": [],
                "note": f"No runbook mapped to {alertname}.",
                "available": sorted(books),
            }
        return {"runbooks": matches}

    @mcp.tool(annotations=READ)
    def search_runbooks(keywords: str) -> list[dict[str, Any]]:
        """Find runbooks by keywords (e.g. "oom memory"). Returns names and titles."""
        words = keywords.lower().split()
        scored = []
        for name, book in books.items():
            haystack = f"{name} {book['title']} {book['body']}".lower()
            score = sum(haystack.count(w) for w in words)
            if score:
                scored.append((score, name, book["title"]))
        return [{"name": n, "title": t} for _, n, t in sorted(scored, reverse=True)[:5]]

    @mcp.tool(annotations=READ)
    def read_runbook(name: str) -> str:
        """Full text of a runbook by name (from search_runbooks)."""
        if name not in books:  # lookup by key: no file paths from the model
            raise ToolError(f"unknown runbook {name!r}; available: {sorted(books)}")
        return str(books[name]["body"])

    return mcp
