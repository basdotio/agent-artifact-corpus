"""Bookmark handles.

A handle is the only thing a client holds between calls. The protocol has no session
to remember it in, so the client gets it back from `add_bookmark` and passes it to every
later tool as an ordinary argument. On a server without authentication the handle is also
the only thing standing between a stranger and the bookmark. The spec's stateful-tools
guidance asks such a handle to carry sufficient entropy and gives a UUIDv4 as its example;
this one carries 128 random bits, a little more than that.
"""

import re
import secrets

PREFIX = "bm_"
_SHAPE = re.compile(r"^bm_[0-9a-f]{32}$")


def new_bookmark_id() -> str:
    """Mint a fresh, unguessable handle."""
    return f"{PREFIX}{secrets.token_hex(16)}"


def is_bookmark_id(value: str) -> bool:
    """True when `value` has the shape of a handle this server minted."""
    return _SHAPE.fullmatch(value) is not None
