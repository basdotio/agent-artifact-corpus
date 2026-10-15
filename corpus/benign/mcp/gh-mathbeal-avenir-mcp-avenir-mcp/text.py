# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Text written by banks, merchants and anyone who can pay you, made safe to show.

Payee names and memos are untrusted. Shown as they are, a line break could add a
forged line to a confirmation question, and a right-to-left override or a
zero-width character could make one name look like another.
"""

from __future__ import annotations

import unicodedata
from typing import Annotated

from pydantic import AfterValidator

MAX_TEXT = 80

MAX_PAYEE = 200
"""YNAB refuses a payee_name longer than this."""
MAX_MEMO = 500
"""YNAB refuses a memo longer than this."""


def _without_nul(value: str) -> str:
    """Refuse the one character YNAB rejects in any text: NUL.

    Args:
        value: A payee name or memo about to be sent to YNAB.

    Returns:
        The value, unchanged.

    Raises:
        ValueError: If it contains U+0000, with what to do.
    """
    if "\x00" in value:
        raise ValueError("contains a NUL character (U+0000), which YNAB refuses: remove it")
    return value


YnabText = Annotated[str, AfterValidator(_without_nul)]
"""Text avenir-mcp sends to YNAB: without NUL, which YNAB answers with a 400."""

# Control characters, line and paragraph separators: shown as a space.
_BREAKS = {"Cc", "Zl", "Zp"}
# Format characters (zero-width, direction overrides, soft hyphen): dropped.
_INVISIBLE = {"Cf"}


def one_line(name: str) -> str:
    """Refuse a name that would not show on one line of visible characters.

    A name the agent chooses appears in the question the user confirms: a line break
    in it would add a line of the agent's choosing.

    Args:
        name: A name about to be sent to YNAB, such as a new category's.

    Returns:
        The name, unchanged.

    Raises:
        ValueError: If it holds a line break, a control or a format character, with
            what to do.
    """
    if any(unicodedata.category(char) in _BREAKS | _INVISIBLE for char in name):
        raise ValueError(
            f"{untrusted(name)!r} contains a line break, control or format character "
            "(such as a zero-width or direction mark): give the name on one line, with "
            "visible characters only."
        )
    return name


def untrusted(text: str | None) -> str:
    """Make bank text safe to show: one line of visible characters.

    Args:
        text: Text from a bank or a stranger, or None.

    Returns:
        The text on one line: format characters dropped, line breaks and control
        characters turned into spaces, runs of spaces collapsed; at most MAX_TEXT
        long and marked with … when cut; empty for None.
    """
    kept = []
    for char in text or "":
        category = unicodedata.category(char)
        if category in _INVISIBLE:
            continue
        kept.append(" " if category in _BREAKS else char)
    line = " ".join("".join(kept).split())
    return line if len(line) <= MAX_TEXT else line[: MAX_TEXT - 1] + "…"
