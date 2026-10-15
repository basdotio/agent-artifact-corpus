"""Cursors: a position in a listing, handed to the client and handed back.

A cursor is the other explicit handle this server mints. It names a position in one total
order (newest first: `created_at`, then `bookmark_id` as the tiebreak), and the next page is
every row strictly after it. A row removed between two pages shifts nothing, because the
position is a key, not a count; `OFFSET 20` would skip a row the client never saw.

The encoding is opaque and tagged with the listing it came from, so a cursor from some
other list is refused rather than read as a position in an order it never came from. It is
not signed, because it grants nothing: the read it resumes runs as the caller, like any
other, so a cursor replayed by another owner returns only that owner's rows.
"""

import base64
import binascii
import json

LISTING = "bookmarks:newest-first"


class InvalidCursor(ValueError):
    """The cursor is not a position in this listing."""


def encode(created_at: str, bookmark_id: str) -> str:
    raw = json.dumps([LISTING, created_at, bookmark_id], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode(cursor: str) -> tuple[str, str]:
    """The (created_at, bookmark_id) position, or InvalidCursor."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        parts = json.loads(base64.urlsafe_b64decode(padded))
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursor(cursor) from exc
    if (
        not isinstance(parts, list)
        or len(parts) != 3
        or parts[0] != LISTING
        or not all(isinstance(part, str) for part in parts[1:])
    ):
        raise InvalidCursor(cursor)
    return parts[1], parts[2]
