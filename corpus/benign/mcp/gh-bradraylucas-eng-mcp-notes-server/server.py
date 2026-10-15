# Copyright (c) 2026 Brad Lucas
# SPDX-License-Identifier: MIT
# mcp-notes-server - free and open source (MIT). Full template pack: https://bradray2.gumroad.com
#
"""
notes-server — a minimal Model Context Protocol (MCP) server example.

Tools exposed:
  - create_note: create a note with a title and body
  - list_notes:  list all saved notes
  - search_notes: search notes by keyword (title or body)

Notes are stored as JSON in a local notes.json file next to this script.

Run (requires the official `mcp` Python SDK):
    pip install -r requirements.txt
    python server.py
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

_STORAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.json")
_MAX_TITLE_LEN = 120
_MAX_BODY_LEN = 10_000


def _load_notes() -> dict:
    """Load the notes store; return {"notes": [...]} if missing/corrupt."""
    if not os.path.exists(_STORAGE_PATH):
        return {"notes": []}
    try:
        with open(_STORAGE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("notes"), list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"notes": []}


def _save_notes(data: dict) -> None:
    """Atomically persist the notes store."""
    tmp = _STORAGE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, _STORAGE_PATH)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("notes-server")


@mcp.tool()
def create_note(title: str, body: str = "") -> dict:
    """Create a new note and store it in the local notes.json file.

    Args:
        title: Short title for the note (max 120 characters, required).
        body:  Note body text (max 10,000 characters).

    Returns:
        The created note record, including its id and timestamps.
    """
    title = (title or "").strip()
    body = (body or "").strip()
    if not title:
        raise ValueError("title is required and cannot be empty")
    if len(title) > _MAX_TITLE_LEN:
        raise ValueError(f"title too long (max {_MAX_TITLE_LEN} chars)")
    if len(body) > _MAX_BODY_LEN:
        raise ValueError(f"body too long (max {_MAX_BODY_LEN} chars)")

    data = _load_notes()
    note = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "body": body,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    data["notes"].append(note)
    _save_notes(data)
    return note


@mcp.tool()
def list_notes(limit: int = 50) -> list:
    """List saved notes, newest first.

    Args:
        limit: Maximum number of notes to return (1-500, default 50).
    """
    limit = max(1, min(int(limit), 500))
    data = _load_notes()
    # Newest first; insertion index breaks ties for notes created in the same second.
    ordered = sorted(enumerate(data["notes"]), key=lambda p: (p[1].get("created_at", ""), p[0]), reverse=True)
    return [n for _, n in ordered[:limit]]


@mcp.tool()
def search_notes(query: str) -> list:
    """Search notes by keyword in title or body (case-insensitive).

    Args:
        query: Keyword or phrase to search for.
    """
    query = (query or "").strip()
    if not query:
        raise ValueError("query is required")
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    matches = [
        n
        for n in _load_notes()["notes"]
        if pattern.search(n.get("title", "")) or pattern.search(n.get("body", ""))
    ]
    ordered = sorted(enumerate(matches), key=lambda p: (p[1].get("created_at", ""), p[0]), reverse=True)
    return [n for _, n in ordered]


if __name__ == "__main__":
    mcp.run()
