"""Opaque continuation cursors.

A cursor records the snapshot, the request it continues and a position. It
carries no access rights: every page is authorized again. A cursor from a
snapshot that is no longer current is rejected so pages from different
revisions are never combined.
"""

import base64
import binascii
import json
from typing import Any, Dict, Optional


class CursorError(ValueError):
    """Raised for malformed, mismatched or expired cursors."""


def encode_cursor(snapshot_id: str, target: str, offset: int) -> str:
    """Encode a continuation cursor."""
    raw = json.dumps(
        {"s": snapshot_id, "t": target, "o": offset}, separators=(",", ":")
    )
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: Optional[str], snapshot_id: str, target: str) -> int:
    """Return the offset for `cursor` (0 when absent).

    Raises:
        CursorError: If the cursor is malformed, for another request, or from
            another snapshot (restart required).
    """
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data: Dict[str, Any] = json.loads(base64.urlsafe_b64decode(padded.encode()))
        offset = int(data["o"])
    except (binascii.Error, ValueError, KeyError, TypeError) as e:
        raise CursorError("invalid cursor") from e
    if data.get("t") != target or offset < 0:
        raise CursorError("cursor does not belong to this request")
    if data.get("s") != snapshot_id:
        raise CursorError(
            "the knowledge snapshot changed since this cursor was issued; "
            "restart from the first page"
        )
    return offset
