"""Bounds for descriptive metadata returned to an MCP client.

These limits apply to labels and previews, not operational URLs or literal
source excerpts. Truncating excerpt text would break citation offsets; URLs
are either preserved whole or rejected/skipped by the caller.
"""

from typing import Final

MAX_TITLE_CHARS: Final = 512
MAX_SNIPPET_CHARS: Final = 2_000
MAX_ENGINE_CHARS: Final = 256
MAX_ENGINE_NAME_CHARS: Final = 128
MAX_HEADING_CHARS: Final = 512
MAX_GAP_CHARS: Final = 2_000
MAX_ERROR_CHARS: Final = 1_000
MAX_HINT_CHARS: Final = 2_000
MAX_UNRESPONSIVE_ENGINES: Final = 50


def truncate_metadata(value: str, limit: int) -> str:
    """Return a deterministic bounded metadata string.

    A trailing ellipsis marks truncation while keeping the returned string at
    or below ``limit`` Unicode characters.
    """
    if len(value) <= limit:
        return value
    if limit <= 0:
        return ""
    if limit == 1:
        return "…"
    return value[: limit - 1] + "…"
