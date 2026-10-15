"""MCP server (FastMCP) for Docmost.

Exposes Docmost's REST API as MCP tools so that an LLM can search, read,
create and update pages, and manage spaces and comments.

Local run (stdio, for Claude Desktop / Cursor)::

    uv run docmost-mcp-oss

Remote run (HTTP)::

    uv run docmost-mcp-oss --http --port 8000

Environment variables (see .env.example): DOCMOST_URL and either DOCMOST_API_KEY
or DOCMOST_EMAIL + DOCMOST_PASSWORD.

The exposed tools are the subset of endpoints verified against real
instances; see `docs/DOCMOST-API.md`.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

from fastmcp import FastMCP

from .client import DocmostClient, DocmostError

mcp = FastMCP(
    "Docmost",
    instructions=(
        'MCP server for a Docmost workspace. To answer "what is in this '
        'workspace?" or to get an inventory, start with '
        "`get_workspace_overview`, which lists every space and every page "
        "(including nested ones). Then `get_page` reads a page (returns "
        "Markdown) and `search_pages` finds one by keyword. "
        "To create content use `create_page` with Markdown; to "
        "**replace the body of an existing page** use "
        "`update_page_content` (via the Yjs WebSocket, takes ~13 s); to "
        "rename, `update_page`. "
        "Space IDs are UUIDs; so are page IDs (`slugId` is the "
        "short identifier that appears in the URL)."
    ),
)

# Single client, lazily authenticated and reused.
_client: DocmostClient | None = None


async def _get_client() -> DocmostClient:
    global _client
    if _client is None:
        _client = DocmostClient.from_env()
    await _client.authenticate()
    return _client


def _load_dotenv() -> None:
    """Loads a .env from the current directory if `python-dotenv` is available."""
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        return
    load_dotenv()


# ====================================================================== #
# Tool annotations
# ====================================================================== #
# MCP hints, not guarantees: a client uses them to decide what it may call
# without asking (a read-only tool is safe to auto-approve, a destructive one
# is not), and directories such as OpenAI's reject a tool that leaves any of
# the four out. Every tool here talks to a remote Docmost, so `openWorldHint`
# is always true.


def _hints(
    *,
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = False,
) -> dict[str, bool]:
    """Builds the annotation hints of a tool.

    Args:
        read_only: the tool does not modify the workspace.
        destructive: it can overwrite or remove existing data. Only meaningful
            when `read_only` is false; a tool that only adds data is not
            destructive.
        idempotent: calling it again with the same arguments leaves the
            workspace in the same state.

    Returns:
        The four hints the MCP specification defines, all of them booleans.
    """
    if read_only and (destructive or not idempotent):
        raise ValueError("a read-only tool is neither destructive nor non-idempotent")
    return {
        "readOnlyHint": read_only,
        "destructiveHint": destructive,
        "idempotentHint": idempotent,
        "openWorldHint": True,
    }


# ====================================================================== #
# Tools — Pages
# ====================================================================== #
@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def search_pages(
    query: str,
    space_id: str | None = None,
    limit: int = 20,
) -> dict:
    """Searches pages by keyword (full-text search).

    It is a lexical search (PostgreSQL FTS): use meaningful words. Empty-meaning
    terms ("a", "de", "the") are stopwords and return no results.

    Args:
        query: Search terms, e.g. "docker compose".
        space_id: UUID of the space to limit the search to. If omitted, it
            searches all accessible spaces and merges them by relevance.
        limit: Maximum number of results (1-100).
    """
    client = await _get_client()
    return await client.search_pages(query, space_id=space_id, limit=limit)


@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def get_page(page_id: str, format: str = "markdown") -> dict:
    """Fetches a page: metadata **and** content.

    Returns the page's metadata plus the `content` field with the full text.
    Internally it combines `/pages/info` with `/pages/export`.

    Args:
        page_id: UUID or slugId of the page.
        format: Content format: 'markdown' (recommended) or 'html'.
    """
    client = await _get_client()
    return await client.get_page(page_id, format=format)


# Creating is additive, and a second call makes a second page.
@mcp.tool(annotations=_hints())
async def create_page(
    space_id: str,
    title: str | None = None,
    content: str | None = None,
    parent_page_id: str | None = None,
    format: str = "markdown",
) -> dict:
    """Creates a new page in a space, with or without content.

    If you provide `content`, the page is uploaded through the import endpoint
    (`/pages/import`), which is the only REST way that persists the page body
    in Docmost. The title is taken from the first heading; if you also provide
    `title`, that one is used.

    Args:
        space_id: UUID of the destination space.
        title: Title of the page (optional).
        content: Page content in Markdown (recommended).
        parent_page_id: ID of the parent page to nest it under (optional).
        format: Format of `content`: 'markdown' or 'html'.
    """
    client = await _get_client()
    return await client.create_page(
        space_id,
        title=title,
        content=content,
        parent_page_id=parent_page_id,
        format=format,
    )


# Renaming overwrites the previous title, and repeating it changes nothing.
@mcp.tool(annotations=_hints(destructive=True, idempotent=True))
async def update_page(page_id: str, title: str | None = None) -> dict:
    """Renames a page.

    To change the **content**, use `update_page_content`.

    Args:
        page_id: UUID or slugId of the page.
        title: New title.
    """
    client = await _get_client()
    return await client.update_page(page_id, title=title)


# "replace" overwrites the body, and append/prepend make a retry unsafe.
@mcp.tool(annotations=_hints(destructive=True))
async def update_page_content(
    page_id: str,
    markdown: str,
    mode: str = "replace",
) -> dict:
    """**Writes into the body** of an already-created page.

    Docmost's REST API cannot do this — the body lives in the Yjs collaboration
    server — so this tool opens the collaboration WebSocket, edits the document
    and waits for it to be persisted (~13 s).

    Unlike `/pages/update`, which accepts an `operation` field and ignores it,
    `mode` genuinely works here:

    - `"replace"` (default): the page ends up with exactly this Markdown.
    - `"append"`: keeps what is there and adds this at the end.
    - `"prepend"`: keeps what is there and adds this at the start.

    The Markdown is converted with Docmost's own converter, so it supports its
    whole schema: headings, bold, italics, code, lists, tables, blockquotes,
    code blocks, etc.

    Requires the `yjs` extra (`uv sync --extra yjs`).

    Args:
        page_id: UUID or slugId of the page to edit.
        markdown: Content to write, in Markdown.
        mode: `"replace"`, `"append"` or `"prepend"`.
    """
    try:
        from .collab import CollabError
        from .collab import update_page_content as _update
    except ImportError as exc:  # missing extra
        raise RuntimeError("The 'yjs' extra is not installed. Run: uv sync --extra yjs") from exc

    client = await _get_client()
    try:
        return await _update(client, page_id, markdown, mode=mode)
    except CollabError as exc:
        raise RuntimeError(f"Could not edit the body: {exc}") from exc


# It takes the page out of the workspace (recoverable from the trash).
@mcp.tool(annotations=_hints(destructive=True, idempotent=True))
async def delete_page(page_id: str) -> dict:
    """Moves a page to the trash (recoverable with `restore_page`).

    Args:
        page_id: UUID or slugId of the page.
    """
    client = await _get_client()
    return await client.delete_page(page_id)


# It puts the page back; nothing is overwritten.
@mcp.tool(annotations=_hints(idempotent=True))
async def restore_page(page_id: str) -> dict:
    """Restores a page that is in the trash.

    Args:
        page_id: UUID or slugId of the page.
    """
    client = await _get_client()
    return await client.restore_page(page_id)


# Reordering moves data around, it does not lose it.
@mcp.tool(annotations=_hints(idempotent=True))
async def move_page(
    page_id: str,
    parent_page_id: str | None = None,
    after: str | None = None,
    before: str | None = None,
) -> dict:
    """Moves or reorders a page. Say where it should go; the position is computed.

    Three ways to place a page, in order of preference:

    - **Nest it**: pass `parent_page_id` and the page becomes a child of that
      page (appended at the end of its children by default).
    - **Reorder it**: pass `after` or `before` with the id of a sibling to sit
      next to.
    - Neither: the page is appended at the end of its current parent.

    You never have to invent a position. Docmost orders pages with *fractional
    indexing* — a base62 string it compares lexicographically, which must be
    5-12 characters — and that is fiddly to get right by hand. This tool reads
    the neighbouring positions and generates a valid one in between.

    Args:
        page_id: UUID or slugId of the page to move.
        parent_page_id: UUID or slugId of the new parent. Omit it to leave the
            page where it is.
        after: UUID or slugId of the sibling this page should follow.
        before: UUID or slugId of the sibling this page should precede.
    """
    client = await _get_client()
    return await client.move_page(
        page_id,
        parent_page_id=parent_page_id,
        after=after,
        before=before,
    )


@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def list_recent_pages(space_id: str | None = None, limit: int = 20) -> list[dict]:
    """Lists recently updated pages.

    Args:
        space_id: UUID of the space (optional; without it, from the whole workspace).
        limit: Maximum number of results.
    """
    client = await _get_client()
    return await client.list_recent_pages(space_id=space_id, limit=limit)


@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def get_workspace_overview(
    space_id: str | None = None,
    max_pages: int = 500,
    activity: str = "recent",
    check_empty: bool = False,
) -> dict:
    """**Start here.** Lists everything in the workspace: every space and every page.

    Use this to answer questions like "what do I have in Docmost?", to take an
    inventory, or to find a page by title before reading it with `get_page`.
    Unlike `list_child_pages`, it walks the whole page tree, so nested pages are
    included.

    Each page carries `id`, `slug_id`, `title`, `parent_page_id` and `depth`,
    which is enough to rebuild the tree or to list everything flat.

    With an `activity` level above `"none"` each page also carries `updated_at`
    and `updated_by`, and the result includes `recently_updated`: the most
    recently touched pages, newest first. Use it to decide what is worth reading
    first instead of walking the inventory blindly.

    It also returns a `summary` with counts per space, tree shape (roots,
    containers, leaves, max depth), date ranges and recency buckets, pages never
    edited after creation, top editors and any orphaned pages. Every figure comes
    from data already gathered, so it costs nothing extra; `summary.date_coverage`
    states how much of the workspace the date-based numbers actually cover.

    Args:
        space_id: UUID of a single space to limit the listing (optional).
            Without it, every space the user can access is included.
        max_pages: Safety cap on the total number of pages returned.
        activity: How much activity data to gather:
            `"recent"` (default) reads the recent-pages window, so pages touched
            recently get dates; `"full"` additionally fetches each page to date
            all of them, which costs one request per page and is slow on large
            workspaces; `"none"` skips activity entirely.
        check_empty: When True, downloads each page to measure its body and flag
            the empty ones. Nothing cheaper exposes page size, so this costs one
            request per page — leave it off unless you specifically need it.
    """
    if activity not in ("none", "recent", "full"):
        raise ValueError("activity must be 'none', 'recent' or 'full'")

    client = await _get_client()
    spaces = [await client.get_space(space_id)] if space_id else await client.list_spaces(limit=100)

    described: list[dict] = []
    remaining = max(1, max_pages)
    for space in spaces:
        if not isinstance(space, dict) or not space.get("id"):
            continue
        pages = await client.list_all_pages(space_id=space["id"], max_pages=remaining)
        remaining -= len(pages)
        described.append(
            {
                "id": space["id"],
                "name": space.get("name"),
                "slug": space.get("slug"),
                "page_count": len(pages),
                "pages": pages,
            }
        )
        if remaining <= 0:
            break

    result: dict = {
        "total_pages": sum(s["page_count"] for s in described),
        "total_spaces": len(described),
        "truncated": remaining <= 0,
        "spaces": described,
    }
    if activity == "none":
        return result

    # `/pages/sidebar-pages`, which the tree walk uses, carries no dates. The
    # recent window is a single request and covers the pages most likely to
    # matter; `full` tops it up with a per-page lookup for everything else.
    known: dict[str, dict] = {
        page["id"]: page
        for page in await client.list_recent_pages(limit=max(1, max_pages))
        if page.get("id")
    }
    if activity == "full":
        for space in described:
            for page in space["pages"]:
                if page["id"] in known:
                    continue
                detail = await client.request("/pages/info", {"pageId": page["id"]})
                if isinstance(detail, dict):
                    known[page["id"]] = detail

    names = {
        member["id"]: member.get("name") or member.get("email") or member["id"]
        for member in await client.list_workspace_members(limit=200)
        if member.get("id")
    }

    def annotate(page: dict) -> dict:
        detail = known.get(page["id"], {})
        updated_by = detail.get("lastUpdatedById")
        return {
            **page,
            "updated_at": detail.get("updatedAt"),
            "updated_by": names.get(updated_by) if updated_by else None,
        }

    for space in described:
        space["pages"] = [annotate(page) for page in space["pages"]]

    if check_empty:
        # One export per page: the metadata endpoints never expose the body.
        for space in described:
            for page in space["pages"]:
                try:
                    exported = await client.export_page(page["id"], format="markdown")
                except DocmostError:
                    continue
                body = exported.get("content") or ""
                page["content_chars"] = len(body)
                page["empty"] = _body_is_empty(body)

    recently = sorted(known.values(), key=lambda p: p.get("updatedAt") or "", reverse=True)
    result["activity"] = activity
    result["recently_updated"] = [
        {
            "id": page.get("id"),
            "title": page.get("title"),
            "space": (page.get("space") or {}).get("name"),
            "updated_at": page.get("updatedAt"),
            "updated_by": names.get(page.get("lastUpdatedById"))
            if page.get("lastUpdatedById")
            else None,
        }
        for page in recently[:25]
    ]
    result["summary"] = _summarize(described, known, activity)
    return result


def _body_is_empty(markdown: str) -> bool:
    """True when a page has no body.

    An exported page always renders its title as a leading `# ...` heading, so
    that line is dropped before deciding whether anything is left.
    """
    lines = markdown.strip().splitlines()
    if lines and lines[0].lstrip().startswith("# "):
        lines = lines[1:]
    return not "\n".join(lines).strip()


def _parse_ts(value: str | None):
    """Parses an ISO timestamp; Python 3.10's fromisoformat rejects a trailing Z."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _summarize(described: list[dict], known: dict[str, dict], activity: str) -> dict:
    """Executive summary computed from metadata only.

    Every figure comes from what the tree walk and the activity lookups already
    returned, so this costs no extra requests. `date_coverage` states how much
    of the workspace the date-based numbers actually cover, because with
    `activity="recent"` only the recent window carries timestamps.
    """
    pages = [page for space in described for page in space["pages"]]
    ids = {page["id"] for page in pages}

    dated = [page for page in pages if page.get("updated_at")]
    stamps = sorted(s for s in (_parse_ts(p["updated_at"]) for p in dated) if s)
    now = datetime.now(timezone.utc)

    def within(days: int) -> int:
        cutoff = now - timedelta(days=days)
        return sum(1 for s in stamps if s >= cutoff)

    # A page whose parent is not part of the tree is unreachable from the roots.
    orphaned = [
        {"id": p["id"], "title": p["title"], "parent_page_id": p["parent_page_id"]}
        for p in pages
        if p.get("parent_page_id") and p["parent_page_id"] not in ids
    ]

    # createdAt is only available through the activity lookups.
    never_edited = 0
    for page in pages:
        detail = known.get(page["id"])
        if detail and detail.get("createdAt") and detail.get("updatedAt"):
            if detail["createdAt"] == detail["updatedAt"]:
                never_edited += 1

    editors: dict[str, int] = {}
    for page in pages:
        if page.get("updated_by"):
            editors[page["updated_by"]] = editors.get(page["updated_by"], 0) + 1

    return {
        "spaces": len(described),
        "pages": len(pages),
        "by_space": [{"name": s["name"], "pages": s["page_count"]} for s in described],
        "roots": sum(1 for p in pages if p["depth"] == 0),
        "containers": sum(1 for p in pages if p["has_children"]),
        "leaves": sum(1 for p in pages if not p["has_children"]),
        "max_depth": max((p["depth"] for p in pages), default=0),
        "dated_pages": len(dated),
        "date_coverage": ("every page" if activity == "full" else "recent window only"),
        "oldest_updated_at": stamps[0].isoformat() if stamps else None,
        "newest_updated_at": stamps[-1].isoformat() if stamps else None,
        "span_days": (stamps[-1] - stamps[0]).days if len(stamps) > 1 else 0,
        "updated_last_7_days": within(7),
        "updated_last_30_days": within(30),
        "never_edited": never_edited,
        "orphaned_pages": orphaned,
        "empty_pages": [
            {"id": p["id"], "title": p["title"], "space": space_name}
            for space_name, p in (
                (s["name"], page) for s in described for page in s["pages"] if page.get("empty")
            )
        ]
        if any("empty" in page for s in described for page in s["pages"])
        else None,
        "top_editors": [
            {"name": name, "pages": count}
            for name, count in sorted(editors.items(), key=lambda kv: kv[1], reverse=True)[:5]
        ],
    }


@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def list_child_pages(
    space_id: str | None = None,
    page_id: str | None = None,
    limit: int = 100,
) -> dict:
    """Lists only the **direct** children of a space or a page.

    This is one level, not the whole tree. To enumerate everything in the
    workspace, use `get_workspace_overview` instead.

    Args:
        space_id: UUID of the space whose root pages you want.
        page_id: UUID or slugId of the parent page whose children you want
            (the `space_id` is resolved automatically).
        limit: Maximum number of results.
    """
    if not space_id and not page_id:
        raise ValueError(
            "Provide space_id or page_id. To list the whole workspace, use get_workspace_overview."
        )
    client = await _get_client()
    return {"items": await client.list_child_pages(space_id=space_id, page_id=page_id, limit=limit)}


@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def get_page_breadcrumbs(page_id: str) -> list[dict]:
    """Returns the ancestor path (breadcrumbs) of a page.

    Args:
        page_id: UUID or slugId of the page.
    """
    client = await _get_client()
    return await client.get_page_breadcrumbs(page_id)


@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def get_page_history(page_id: str) -> list[dict]:
    """Lists the version history of a page.

    Args:
        page_id: UUID or slugId of the page.
    """
    client = await _get_client()
    return await client.get_page_history(page_id)


# ====================================================================== #
# Tools — Spaces
# ====================================================================== #
@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def list_spaces(limit: int = 50) -> list[dict]:
    """Lists the spaces the user has access to.

    Args:
        limit: Maximum number of spaces to return.
    """
    client = await _get_client()
    return await client.list_spaces(limit=limit)


@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def get_space(space_id: str) -> dict:
    """Gets the details of a space.

    Args:
        space_id: UUID of the space.
    """
    client = await _get_client()
    return await client.get_space(space_id)


# Creating is additive, and a second call makes a second space.
@mcp.tool(annotations=_hints())
async def create_space(name: str, slug: str | None = None, description: str | None = None) -> dict:
    """Creates a new space.

    Args:
        name: Name of the space.
        slug: Identifier for the URL. **Letters and numbers only** (no
            hyphens or underscores), e.g. 'mySpace'.
        description: Description (optional).
    """
    client = await _get_client()
    return await client.create_space(name, slug=slug, description=description)


# ====================================================================== #
# Tools — Comments
# ====================================================================== #
@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def get_comments(page_id: str, limit: int = 50) -> list[dict]:
    """Gets the comments of a page.

    Args:
        page_id: UUID or slugId of the page.
        limit: Maximum number of comments.
    """
    client = await _get_client()
    return await client.get_comments(page_id, limit=limit)


# Creating is additive, and a second call makes a second comment.
@mcp.tool(annotations=_hints())
async def create_comment(
    page_id: str,
    content: str,
    parent_comment_id: str | None = None,
) -> dict:
    """Adds a comment to a page.

    Args:
        page_id: UUID or slugId of the page.
        content: Content as a **JSON string** of a Tiptap document, e.g.
            '{"type":"doc","content":[{"type":"paragraph","content":'
            '[{"type":"text","text":"Hello"}]}]}'.
        parent_comment_id: UUID of the parent comment to reply to (optional).
    """
    client = await _get_client()
    return await client.create_comment(page_id, content, parent_comment_id=parent_comment_id)


# It replaces the previous content of the comment.
@mcp.tool(annotations=_hints(destructive=True, idempotent=True))
async def update_comment(comment_id: str, content: str) -> dict:
    """Updates the content of a comment.

    Args:
        comment_id: UUID of the comment.
        content: New content as a Tiptap JSON string.
    """
    client = await _get_client()
    return await client.update_comment(comment_id, content)


# ====================================================================== #
# Tools — User / workspace
# ====================================================================== #
@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def get_current_user() -> dict:
    """Returns the authenticated user and workspace information."""
    client = await _get_client()
    return await client.get_current_user()


@mcp.tool(annotations=_hints(read_only=True, idempotent=True))
async def list_workspace_members(limit: int = 50) -> list[dict]:
    """Lists the members of the workspace.

    Args:
        limit: Maximum number of members to return.
    """
    client = await _get_client()
    return await client.list_workspace_members(limit=limit)


# ====================================================================== #
# Entry point
# ====================================================================== #
def main() -> None:
    _load_dotenv()

    parser = argparse.ArgumentParser(description="MCP server for Docmost")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use HTTP (streamable-http) transport instead of stdio.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only verify the connection and authentication with Docmost.",
    )
    args = parser.parse_args()

    if not os.getenv("DOCMOST_URL"):
        print("ERROR: define DOCMOST_URL (see .env.example)", file=sys.stderr)
        sys.exit(1)

    if args.check:
        import asyncio

        async def _check() -> None:
            client = DocmostClient.from_env()
            try:
                me = await client.get_current_user()
                user = (me or {}).get("user", {})
                print(f"OK: authenticated as {user.get('email', '?')} ({client.base_url})")
            except DocmostError as exc:
                print(f"FAIL: {exc}", file=sys.stderr)
                sys.exit(1)
            finally:
                await client.aclose()

        asyncio.run(_check())
        return

    if args.http:
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
