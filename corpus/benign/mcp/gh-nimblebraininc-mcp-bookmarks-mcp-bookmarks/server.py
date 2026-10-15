"""Bookmarks MCP server.

A remote MCP server on the 2026-07-28 revision of the protocol. The process holds no state
between requests: every bookmark lives in the store, and a client that wants one back
names it with the handle it was given. Any process with the same database file answers
any request, which is what lets the server run as more than one replica.
"""

import logging
import sys
from functools import lru_cache
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.tools import ToolResult
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import __version__
from .annotations import ADDS, CHANGES, READS
from .auth import build_auth, current_owner
from .config import MCP_PATH, Settings
from .errors import ERROR_SCHEMA, not_a_cursor, not_a_handle, not_a_web_url, not_found
from .ids import is_bookmark_id
from .models import Bookmark, BookmarkPage, Deleted
from .paging import InvalidCursor
from .store import MAX_LIMIT, UNSET, Store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_bookmarks")


@lru_cache
def open_store(path: str) -> Store:
    return Store(path)


def schema(model: type[BaseModel]) -> dict:
    """The output schema of a tool that returns `model` or a refusal.

    A tool whose return type is `Model | ToolResult` gets no derived output schema, so each
    tool names its shape here. The shape is a union: a refusal's `structuredContent` is the
    error envelope, and the spec holds every structured result to the declared schema,
    error results included.
    """
    success = model.model_json_schema()
    # A nested model lands in `$defs` and is referenced as `#/$defs/...`, a pointer from
    # the schema's root, so the definitions have to sit at the root of the union.
    defs = success.pop("$defs", None)
    union: dict = {"type": "object", "oneOf": [success, ERROR_SCHEMA]}
    if defs:
        union["$defs"] = defs
    return union


def _title(title: str | None) -> str | None:
    """A blank title is no title."""
    cleaned = (title or "").strip()
    return cleaned or None


def web_url(url: str) -> str | ToolResult:
    cleaned = url.strip()
    if not cleaned.lower().startswith(("http://", "https://")):
        return not_a_web_url(url)
    return cleaned


def create_server(settings: Settings) -> FastMCP:
    """The server for these settings. Built once per process; tests build their own."""
    mcp = FastMCP(
        "Bookmarks",
        version=__version__,
        instructions=(
            "Saves links for later. add_bookmark returns a bookmark_id; every other tool takes "
            "that handle. There is no current bookmark and no session: pass the handle each time."
        ),
        # A refusal is returned with its envelope (errors.py). Anything that gets as far as
        # an unexpected exception is a bug, and its text stays out of the result.
        mask_error_details=True,
        auth=build_auth(settings),
    )

    def store() -> Store:
        return open_store(settings.db_path)

    def find(bookmark_id: str) -> Bookmark | ToolResult:
        """The caller's bookmark, or the refusal to return in its place. A handle that
        belongs to someone else gets the same refusal as one that was never minted."""
        if not is_bookmark_id(bookmark_id):
            return not_a_handle(bookmark_id)
        bookmark = store().get(current_owner(), bookmark_id)
        return bookmark if bookmark is not None else not_found(bookmark_id)

    @mcp.tool(annotations=ADDS, output_schema=schema(Bookmark))
    def add_bookmark(
        url: Annotated[str, Field(description="Full http:// or https:// address to save.")],
        title: Annotated[
            str | None, Field(description="Display title. Leave empty when the user gave none.")
        ] = None,
        tags: Annotated[
            list[str] | None,
            Field(
                description="Tags to file it under, such as ['mcp', 'reading']. Case does not matter."
            ),
        ] = None,
    ) -> Bookmark | ToolResult:
        """Save a link the user wants to keep, and get back the handle for it.

        Call this when the user shares a URL and asks to save, keep, or bookmark it. The
        result's bookmark_id is the handle every other tool takes, so keep it. A bookmark is
        kept until delete_bookmark removes it. Saving the same URL twice makes two
        bookmarks; call list_bookmarks first if you are unsure whether the link is already
        saved.
        """
        cleaned = web_url(url)
        if isinstance(cleaned, ToolResult):
            return cleaned
        return store().add(current_owner(), cleaned, _title(title), tags)

    @mcp.tool(annotations=READS, output_schema=schema(Bookmark))
    def get_bookmark(
        bookmark_id: Annotated[
            str, Field(description="Handle from add_bookmark or list_bookmarks.")
        ],
    ) -> Bookmark | ToolResult:
        """Read one bookmark by its handle.

        Call this when you hold a bookmark_id and need its URL, title, or tags. It does not
        search; to find a bookmark by tag, call list_bookmarks.
        """
        return find(bookmark_id)

    @mcp.tool(annotations=READS, output_schema=schema(BookmarkPage))
    def list_bookmarks(
        tag: Annotated[
            str | None, Field(description="Only bookmarks carrying this tag. Omit for all.")
        ] = None,
        include_archived: Annotated[
            bool, Field(description="Also return bookmarks that were archived.")
        ] = False,
        limit: Annotated[int, Field(ge=1, le=MAX_LIMIT, description="Page size, 1 to 100.")] = 20,
        cursor: Annotated[
            str | None,
            Field(
                description=(
                    "Position from a previous page's next_cursor. Omit for the first page. "
                    "Pass the same tag and include_archived as that page."
                )
            ),
        ] = None,
    ) -> BookmarkPage | ToolResult:
        """List saved bookmarks, newest first, one page at a time.

        Call this to show the user what is saved, to find a bookmark by tag, or to check
        whether a URL is already saved before calling add_bookmark. Each item carries its
        bookmark_id. When next_cursor is set, call again with cursor=next_cursor and the
        same filters to get the next page; it is null on the last page.
        """
        try:
            items, next_cursor = store().list_page(
                current_owner(),
                tag=tag,
                include_archived=include_archived,
                limit=limit,
                cursor=cursor,
            )
        except InvalidCursor:
            return not_a_cursor(cursor or "")
        if next_cursor is not None:
            next_step = (
                "More bookmarks match. Call list_bookmarks again with cursor set to "
                "next_cursor and the same tag and include_archived."
            )
        elif cursor is not None:
            next_step = (
                "This is the last page. Bookmarks saved since the first page sort before it; "
                "call list_bookmarks again without cursor to see them."
            )
        else:
            next_step = "This is the whole list."
        return BookmarkPage(items=items, next_cursor=next_cursor, next_step=next_step)

    @mcp.tool(annotations=CHANGES, output_schema=schema(Bookmark))
    def update_bookmark(
        bookmark_id: Annotated[
            str, Field(description="Handle from add_bookmark or list_bookmarks.")
        ],
        title: Annotated[
            str | None,
            Field(
                description="New title. Omit to keep the current one; pass an empty string to clear it."
            ),
        ] = None,
        tags: Annotated[
            list[str] | None,
            Field(description="Replacement tag list. Omit to keep the current tags."),
        ] = None,
    ) -> Bookmark | ToolResult:
        """Change a bookmark's title or tags.

        Call this when the user wants to rename a bookmark or retag it. Only the fields you
        pass change. To file a bookmark away instead, call archive_bookmark.
        """
        found = find(bookmark_id)
        if isinstance(found, ToolResult):
            return found
        updated = store().update(
            current_owner(),
            bookmark_id,
            title=UNSET if title is None else _title(title),
            tags=UNSET if tags is None else tags,
        )
        assert updated is not None
        return updated

    @mcp.tool(annotations=CHANGES, output_schema=schema(Bookmark))
    def archive_bookmark(
        bookmark_id: Annotated[
            str, Field(description="Handle from add_bookmark or list_bookmarks.")
        ],
    ) -> Bookmark | ToolResult:
        """Archive a bookmark so list_bookmarks stops showing it by default.

        Call this when the user is done with a link but may want it back. Archiving twice is
        harmless. To remove a bookmark for good, call delete_bookmark.
        """
        found = find(bookmark_id)
        if isinstance(found, ToolResult):
            return found
        archived = store().archive(current_owner(), bookmark_id)
        assert archived is not None
        return archived

    @mcp.tool(annotations=CHANGES, output_schema=schema(Deleted))
    def delete_bookmark(
        bookmark_id: Annotated[
            str, Field(description="Handle from add_bookmark or list_bookmarks.")
        ],
    ) -> Deleted | ToolResult:
        """Delete a bookmark permanently.

        Call this only when the user asks to delete or remove a bookmark. There is no undo;
        when the user may want it back, call archive_bookmark instead.
        """
        found = find(bookmark_id)
        if isinstance(found, ToolResult):
            return found
        store().delete(current_owner(), bookmark_id)
        return Deleted(bookmark_id=bookmark_id, deleted=True)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        """Healthy means the one dependency answers: a probe that never touches the store
        would pass on a machine that fails every tool call."""
        body = {"service": "mcp-bookmarks", "version": __version__}
        try:
            store()
        except Exception as exc:
            logger.error("store unavailable: %r", exc)
            return JSONResponse({"status": "unavailable", **body}, status_code=503)
        return JSONResponse({"status": "ok", **body})

    return mcp


def create_app(mcp: FastMCP):
    """The ASGI app a container runs. stateless_http=True keeps the 2025-era handshake from
    minting a session either, so a client on the old era is also answered by any replica."""
    return mcp.http_app(path=MCP_PATH, stateless_http=True)


settings = Settings.from_env()
mcp = create_server(settings)
app = create_app(mcp)  # `uvicorn mcp_bookmarks.server:app`

if __name__ == "__main__":
    import os

    mcp.run(
        transport="http",
        host=os.environ.get("BOOKMARKS_HOST", "127.0.0.1"),
        port=int(os.environ.get("BOOKMARKS_PORT", "8000")),
        path=MCP_PATH,
        stateless_http=True,
    )
