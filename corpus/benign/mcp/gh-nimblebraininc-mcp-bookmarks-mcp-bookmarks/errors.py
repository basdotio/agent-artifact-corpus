"""A tool's own failure is a result, not a protocol error.

The spec gives a tool call two failure channels. A JSON-RPC error is for the request the
server could not take at all: an unknown tool, malformed params. A result with
`isError: true` is for a tool that ran and refused, and the model is meant to read it and
recover. "Bookmark not found" belongs on the second channel, with a body the model can act
on. Raising `ToolError` lands on the right channel but keeps only the message text and
drops `structuredContent`, so refusals here are returned, never raised.

One more rule follows. A tool that declares an `outputSchema` promises that every
`structuredContent` it returns conforms to it, and the spec grants no exception for an
error result. The Python and TypeScript SDK clients skip validation when `isError` is
set; the MCP Inspector does not, and rejects a refusal whose body is the envelope when the
schema describes a bookmark. The schema a tool declares is therefore the union of its
success shape and ERROR_SCHEMA (`server.schema()`).
"""

import json
from typing import Final

from fastmcp.tools import ToolResult
from mcp.types import TextContent

NOT_FOUND: Final = "not_found"
BAD_INPUT: Final = "bad_input"

ERROR_SCHEMA: Final[dict] = {
    "type": "object",
    "properties": {
        "error": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "For software: not_found, bad_input."},
                "message": {"type": "string", "description": "What was wrong."},
                "next_step": {"type": "string", "description": "What to do instead."},
            },
            "required": ["code", "message", "next_step"],
            "additionalProperties": False,
        }
    },
    "required": ["error"],
    "additionalProperties": False,
}
"""The shape of every refusal's structuredContent. Part of every tool's outputSchema."""


def refuse(code: str, message: str, next_step: str) -> ToolResult:
    """An `isError` result whose text block and `structuredContent` carry the same envelope.

    `code` is for software, `message` says what was wrong, `next_step` says what to do
    instead. The text block is the JSON of the same envelope, for a client that reads only
    text.
    """
    envelope = {"error": {"code": code, "message": message, "next_step": next_step}}
    return ToolResult(
        content=[TextContent(type="text", text=json.dumps(envelope))],
        structured_content=envelope,
        is_error=True,
    )


def not_found(bookmark_id: str) -> ToolResult:
    return refuse(
        NOT_FOUND,
        f"No bookmark {bookmark_id}.",
        "Call list_bookmarks to see what exists, then retry with a bookmark_id from the list.",
    )


def not_a_handle(value: str) -> ToolResult:
    return refuse(
        BAD_INPUT,
        f"{value!r} is not a bookmark_id.",
        "Pass the bookmark_id from add_bookmark or list_bookmarks; it looks like bm_ followed "
        "by 32 hex characters.",
    )


def not_a_web_url(value: str) -> ToolResult:
    return refuse(
        BAD_INPUT,
        f"{value!r} is not a web URL.",
        "Give a full http:// or https:// address.",
    )


def not_a_cursor(value: str) -> ToolResult:
    return refuse(
        BAD_INPUT,
        f"{value!r} is not a cursor from list_bookmarks.",
        "Call list_bookmarks again without cursor to start from the first page, and pass only "
        "the next_cursor it returns.",
    )
