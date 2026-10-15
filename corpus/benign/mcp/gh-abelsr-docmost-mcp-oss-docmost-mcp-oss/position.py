"""Fractional indexing for Docmost page positions.

Docmost orders pages by a ``position`` string that is compared
lexicographically (``collate('C')``). The strings are base62 and, as observed on
a real instance, five characters long (``a04Nh``, ``a19lX``, ``a22tq``).

``POST /pages/move`` validates that the value it receives is **between 5 and 12
characters**, which is stricter than what a plain fractional-indexing
implementation produces: ``generateKeyBetween`` happily returns two-character
keys. Hence :func:`key_between`, which produces a correctly ordered key that also
satisfies Docmost's length constraint.

Keys must not end in ``0``: that is the invariant the classic algorithm relies
on to keep producing fresh keys between two neighbours, and the keys Docmost
itself generates honour it.
"""

from __future__ import annotations

#: Docmost's ordering alphabet, base62 in ASCII order.
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE = len(ALPHABET)
_INDEX = {char: value for value, char in enumerate(ALPHABET)}
ZERO = ALPHABET[0]
ONE = ALPHABET[1]
#: A filler from the middle of the alphabet, so it does not sit flush against
#: its neighbours and leave no room for later inserts.
MIDDLE = ALPHABET[BASE // 2]

#: `/pages/move` rejects anything outside this range.
MIN_LENGTH = 5
MAX_LENGTH = 12


class PositionError(ValueError):
    """Raised when a position cannot be produced within Docmost's limits."""


def key_between(
    lower: str | None = None,
    upper: str | None = None,
    *,
    min_length: int = MIN_LENGTH,
    max_length: int = MAX_LENGTH,
) -> str:
    """Returns a key ``k`` with ``lower < k < upper`` (``None`` means unbounded).

    The result is padded to ``min_length`` and never exceeds ``max_length``, so
    it is always accepted by ``/pages/move``.

    >>> key_between()               # a first key
    'a0001'
    >>> key_between("a04Nh")        # after an existing page
    'a04Ni'
    >>> key_between("a04Nh", "a19lX")  # between two pages
    'a0hXk'
    """
    if lower is not None:
        _validate(lower, max_length)
    if upper is not None:
        _validate(upper, max_length)
    if lower is not None and upper is not None and lower >= upper:
        raise PositionError(f"lower ({lower!r}) must sort before upper ({upper!r})")

    key = _generate(lower, upper)
    return _fit(key, lower, upper, min_length, max_length)


def _validate(key: str, max_length: int) -> None:
    if not key:
        raise PositionError("positions cannot be empty")
    if len(key) > max_length:
        raise PositionError(f"position {key!r} is longer than {max_length} characters")
    unknown = set(key) - set(ALPHABET)
    if unknown:
        raise PositionError(f"position {key!r} has characters outside the alphabet: {unknown}")


def _generate(lower: str | None, upper: str | None) -> str:
    if lower is None and upper is None:
        return "a0"
    if upper is None:
        return _increment(lower)
    if lower is None:
        return _decrement(upper)
    return _midpoint(lower, upper)


def _midpoint(lower: str, upper: str | None) -> str:
    """The classic fractional-indexing midpoint between two keys.

    `upper` may be ``None`` further down the recursion, once the shared prefix
    has been consumed and only "something greater than `lower`" is needed.
    """
    if upper is None:
        return _increment(lower)

    # Strip the longest common prefix and recurse on what is left.
    shared = 0
    limit = min(len(lower), len(upper))
    while shared < limit and lower[shared] == upper[shared]:
        shared += 1
    if shared:
        return upper[:shared] + _midpoint(lower[shared:], upper[shared:])

    low_digit = _INDEX[lower[0]] if lower else 0
    high_digit = _INDEX[upper[0]]

    if high_digit - low_digit > 1:
        return ALPHABET[(low_digit + high_digit) // 2]

    # The first digits are adjacent, so the split has to happen further right.
    if len(upper) > 1:
        return upper[:1]
    return ALPHABET[low_digit] + _midpoint(lower[1:], None)


def _increment(key: str) -> str:
    """A key strictly greater than `key`."""
    digits = list(key)
    for index in range(len(digits) - 1, -1, -1):
        value = _INDEX[digits[index]]
        if value < BASE - 1:
            digits[index] = ALPHABET[value + 1]
            return "".join(digits[: index + 1])
    # Every digit was the maximum: append one more.
    return key + ONE


def _decrement(key: str) -> str:
    """A key strictly smaller than `key`.

    Mirrors `_increment`: it borrows from the right rather than jumping to the
    start of the alphabet. Jumping (``a04Nh`` -> ``Zzzzz``) is also valid, but
    it creates neighbours only one character apart, and a few such moves
    saturate the gap for good.
    """
    digits = list(key)
    for index in range(len(digits) - 1, -1, -1):
        value = _INDEX[digits[index]]
        if value > 0:
            digits[index] = ALPHABET[value - 1]
            return "".join(digits[: index + 1])
    raise PositionError(f"no key sorts before {key!r}")


def _grow(
    base: str,
    filler: str,
    *,
    lower: str | None,
    upper: str | None,
    min_length: int,
    max_length: int,
) -> str | None:
    """Extends `base` with `filler` until it is usable, or gives up.

    Appending a character makes a key larger, which is what turns a too-short
    midpoint into a valid position.
    """
    candidate = base
    while True:
        if (
            min_length <= len(candidate) <= max_length
            and (lower is None or candidate > lower)
            and (upper is None or candidate < upper)
        ):
            return candidate
        if len(candidate) >= max_length:
            return None
        candidate += filler


def _fit(
    key: str,
    lower: str | None,
    upper: str | None,
    min_length: int,
    max_length: int,
) -> str:
    """Pads `key` into Docmost's accepted length without breaking the bounds.

    A midpoint between two close keys can come out shorter than `min_length`.
    Padding it with ``"0"`` pins it just above `lower`; padding with ``"1"``
    leaves more room above. When the midpoint sits far below `upper` neither
    fits, and the room is immediately after `lower` instead, so growing `lower`
    itself yields the smallest key that still sorts after it. All four options
    are tried in that order.
    """
    grown = None
    # Order matters. Growing the midpoint is safe: it is a synthetic value, so
    # nothing else is anchored to it. Growing `lower` is the last resort,
    # because it produces a key right next to a real one — and if the filler is
    # "0" the pair is adjacent with no room left between them, so the *next*
    # insert there is impossible. A filler from the middle of the alphabet
    # leaves usable keys in between.
    attempts = [(key, ZERO), (key, ONE)]
    if lower is not None:
        attempts.append((lower, MIDDLE))
    for base, filler in attempts:
        grown = _grow(
            base,
            filler,
            lower=lower,
            upper=upper,
            min_length=min_length,
            max_length=max_length,
        )
        if grown is not None:
            break

    if grown is None:
        raise PositionError(
            f"no position of {min_length}-{max_length} characters fits between "
            f"{lower!r} and {upper!r}; the gap is saturated"
        )
    key = grown

    # Keep the "never ends in zero" invariant so later inserts stay possible.
    if key.endswith(ZERO):
        for candidate_char in ALPHABET[1:]:
            candidate = key[:-1] + candidate_char
            if (lower is None or candidate > lower) and (upper is None or candidate < upper):
                key = candidate
                break

    if len(key) > max_length:
        raise PositionError(f"generated key {key!r} exceeds {max_length} characters")
    if lower is not None and key <= lower:
        raise PositionError(f"generated key {key!r} does not sort after {lower!r}")
    if upper is not None and key >= upper:
        raise PositionError(f"generated key {key!r} does not sort before {upper!r}")
    return key


def first_key() -> str:
    """A valid key to use when the target has no siblings yet."""
    return key_between()


__all__ = [
    "ALPHABET",
    "MAX_LENGTH",
    "MIN_LENGTH",
    "PositionError",
    "first_key",
    "key_between",
]
