"""Input-text validation for MCP tool parameters.

Port of the canonical character rule from ``../architecture-pattern-mcp/src/text_validation.py``
(docs/implementation-guide.md §1.3 rule 1: "reuse it, do not hand-roll a regex"). Behavior is
unchanged: the same strip window semantics, the same disallowed-character set, the same length
and visibility checks, and the same ValueError message shapes.

Rejects: empty and whitespace-only strings, strings whose every visible character is invisible,
strings containing control/format characters (Unicode general category ``C*``) outside the
allowed whitespace set, and strings longer than ``max_length`` after stripping.

Two enforcement layers:
  Layer 1 — Pydantic annotation: fails at the FastMCP protocol boundary before the handler runs.
  Layer 2 — Runtime guard: defence-in-depth for values read back from persistent storage
             (JobsStore SQLite) or passed through internal APIs.
"""

from __future__ import annotations

import unicodedata
from typing import Annotated

from pydantic import AfterValidator, Field, StringConstraints

DOMAIN_MAX_LENGTH = 200
FREETEXT_MAX_LENGTH = 100_000
PATTERN_NAME_MAX_LENGTH = 100


def _is_control_or_format(ch: str) -> bool:
    """True when ``unicodedata.category(ch)`` is a control/format/private/unassigned class (``C*``)."""
    return unicodedata.category(ch).startswith("C")


def _is_letter_or_digit(ch: str) -> bool:
    """True when ``unicodedata.category(ch)`` is a letter (``L*``) or number (``N*``) class."""
    return unicodedata.category(ch)[0] in ("L", "N")


def ensure_printable_text(
    value: str,
    *,
    field: str,
    allow_line_breaks: bool = True,
    max_length: int = FREETEXT_MAX_LENGTH,
) -> str:
    """Strip, validate and return a text parameter.

    Args:
        value: The string value to validate.
        field: Human-readable field name used in error messages.
        allow_line_breaks: Whether ``\\n`` and ``\\r`` are permitted inside the text.
        max_length: Maximum allowed character count after stripping.

    Returns:
        The stripped string (the maximal strip window of the input).

    Raises:
        ValueError: When a disallowed control/format character is present, when the stripped
            text is longer than ``max_length``, or when it contains no visible letter or digit.
    """
    for ch in value:
        if _is_control_or_format(ch) and not (ch == "\t" or (allow_line_breaks and ch in ("\n", "\r"))):
            cat = unicodedata.category(ch)
            raise ValueError(
                f"{field} contains disallowed character U+{ord(ch):04X} "
                f"(category {cat}); control and format characters are not allowed"
            )

    lo = 0
    n = len(value)
    while lo < n and value[lo].isspace():
        lo += 1
    hi = n
    while hi > lo and value[hi - 1].isspace():
        hi -= 1

    if hi - lo > max_length:
        raise ValueError(
            f"{field} exceeds maximum length of {max_length} characters "
            f"(got {hi - lo} after stripping)"
        )
    if not any(_is_letter_or_digit(ch) for ch in value[lo:hi]):
        raise ValueError(
            "Value must contain at least one visible letter or digit; "
            "whitespace-only and invisible-character-only strings are not allowed"
        )
    return value[lo:hi]


def _freetext_validator(value: str) -> str:
    """AfterValidator for free-text fields (description, focus)."""
    return ensure_printable_text(value, field="value", allow_line_breaks=True)


def _domain_validator(value: str) -> str:
    """AfterValidator for domain fields."""
    return ensure_printable_text(value, field="domain", allow_line_breaks=False)


def _pattern_name_validator(value: str) -> str:
    """AfterValidator for pattern name fields."""
    return ensure_printable_text(
        value, field="name", allow_line_breaks=False, max_length=PATTERN_NAME_MAX_LENGTH
    )


PrintableText = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
    Field(min_length=1, max_length=FREETEXT_MAX_LENGTH),
    AfterValidator(_freetext_validator),
]

DomainName = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
    Field(min_length=1, max_length=DOMAIN_MAX_LENGTH),
    AfterValidator(_domain_validator),
]

PatternName = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
    Field(min_length=1, max_length=PATTERN_NAME_MAX_LENGTH),
    AfterValidator(_pattern_name_validator),
]
