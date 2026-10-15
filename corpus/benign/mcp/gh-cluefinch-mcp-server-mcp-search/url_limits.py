"""URL length accounting shared by retrieval and local link discovery."""

from typing import Final

import httpx

MAX_URL_CHARS: Final = 8192


def exceeds_url_limit(url: str) -> bool:
    """Bound both supplied text and HTTPX's serialized URL, including fragments.

    The limit applies to the complete reusable Cluefinch MCP argument, not
    just the HTTP request-target. Fragments count toward this budget even
    though they are not sent in the HTTP request-target.

    This checks size only: it neither rewrites URL identity nor approves a
    destination for fetching. HTTPX parsing errors propagate to the caller.
    """
    return len(url) > MAX_URL_CHARS or len(str(httpx.URL(url))) > MAX_URL_CHARS
