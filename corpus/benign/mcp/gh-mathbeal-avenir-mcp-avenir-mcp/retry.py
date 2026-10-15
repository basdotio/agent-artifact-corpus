# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""When a failed YNAB request may be sent again: never one that could duplicate a change.

A read costs nothing to send twice, so a timeout or a gateway error on a GET is worth
another try. A write is not: once `POST`, `PATCH` or `DELETE` has left, YNAB may have
applied it and answered into a closed connection, and a second copy would create a
second transaction. Only a failure that proves the request never left is sent again,
whatever the method.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable

import httpx

ATTEMPTS = 3
"""Times one request may be sent in all, the first try included."""

BASE = 0.5
"""Seconds of the window the first wait falls in; it doubles after each failure."""

TRANSIENT = frozenset({502, 503, 504})
"""Statuses of a gateway momentarily out, not of a request YNAB read and refused."""

NEVER_SENT = (httpx.ConnectError, httpx.ConnectTimeout)
"""Failures raised before the request leaves: YNAB cannot have acted on it."""

MIN_PAUSE = 60.0
"""Seconds a Retry-After is held to at least: a tiny value would spend the quota again."""

MAX_PAUSE = 3600.0
"""Seconds a Retry-After is held to at most: YNAB counts over one hour."""


class YnabUnavailable(RuntimeError):
    """YNAB could not be reached, or read the request and answered nothing.

    The two call for different things, and the message says which happened: nothing
    was changed and the call can be made again, or a change may or may not have been
    applied and has to be looked at before anything else is sent.
    """


def _repeatable(method: str, failure: Exception | int) -> bool:
    """Say whether sending this request again could neither duplicate nor help nothing.

    Args:
        method: get, patch, post or delete.
        failure: The transport error raised, or the status code YNAB answered.

    Returns:
        True when the request may leave a second time.
    """
    if isinstance(failure, int):
        return method == "get" and failure in TRANSIENT
    if isinstance(failure, NEVER_SENT):
        return True
    return method == "get" and isinstance(failure, httpx.TransportError)


def decide(
    method: str,
    failure: Exception | int,
    attempt: int,
    # A wait, not a secret: where in the window it falls has nothing to guess.
    jitter: Callable[[], float] = random.random,  # noqa: S311
) -> float | None:
    """Say whether a request that failed may be sent again, and after how long.

    The wait falls anywhere in a window that doubles with each failure: full jitter, so
    two agents that fail at the same moment do not come back together. Only the tries
    before the last are followed by a wait, so the longest window is one second.

    Args:
        method: get, patch, post or delete.
        failure: The transport error raised, or the status code YNAB answered.
        attempt: Which try just failed, counting from 1.
        jitter: Says where in the window the wait falls.

    Returns:
        The seconds to wait before the next try, or None when nothing is sent again.
    """
    if attempt >= ATTEMPTS or not _repeatable(method, failure):
        return None
    return jitter() * BASE * 2.0 ** (attempt - 1)


def landed(method: str, failure: Exception) -> bool:
    """Say whether the request may have reached YNAB, so a change may already be applied.

    Args:
        method: get, patch, post or delete.
        failure: The transport error raised.

    Returns:
        True for a write whose failure does not prove it never left.
    """
    return method != "get" and not isinstance(failure, NEVER_SENT)


def no_answer(method: str, failure: Exception, attempts: int) -> str:
    """Write what an agent reads when no answer came back from YNAB.

    Args:
        method: get, patch, post or delete.
        failure: The transport error the last try raised.
        attempts: How many tries were made.

    Returns:
        The message, saying whether anything may have changed and what to do next.
    """
    detail = str(failure)
    cause = f"{type(failure).__name__}: {detail}" if detail else type(failure).__name__
    if landed(method, failure):
        return (
            f"The request reached YNAB but no answer came back ({cause}): the "
            "change may or may not be applied. Check with find_transactions / "
            "get_category_balances before trying again; do not repeat it blindly."
        )
    return (
        f"YNAB could not be reached after {attempts} attempts ({cause}). Nothing "
        "was changed. Try again in a few minutes."
    )


async def answered(
    method: str,
    send: Callable[[], Awaitable[httpx.Response]],
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> httpx.Response:
    """Send a request until YNAB answers something there is no point sending again.

    Args:
        method: get, patch, post or delete.
        send: Sends the request once; called again only when that cannot duplicate.
        sleep: Waits between two tries.

    Returns:
        The answer of the last try, whatever its status.

    Raises:
        YnabUnavailable: When no try reached YNAB, or one reached it and nothing came back.
    """
    # One place below says what went wrong, so the failure and the count of tries that
    # reached it are carried out of the loop rather than told in two voices.
    failure: httpx.TransportError | None = None
    tries = ATTEMPTS
    for attempt in range(1, ATTEMPTS):
        try:
            response = await send()
        except httpx.TransportError as error:
            delay = decide(method, error, attempt)
            if delay is None:
                failure, tries = error, attempt
                break
        else:
            delay = decide(method, response.status_code, attempt)
            if delay is None:
                return response
        await sleep(delay)
    if failure is None:
        # Nothing follows the last try, so what it gives is the answer or the failure.
        try:
            return await send()
        except httpx.TransportError as error:
            failure = error
    raise YnabUnavailable(no_answer(method, failure, tries)) from failure


def pause_after(header: str | None) -> float | None:
    """Read the pause YNAB's Retry-After asks for, as a count of seconds.

    Args:
        header: The Retry-After header, or None when the answer carried none.

    Returns:
        The seconds to send nothing for, between MIN_PAUSE and MAX_PAUSE, or None when
        the header is absent or is not a count of seconds.
    """
    if header is None or not header.strip().isdigit():
        return None
    return min(MAX_PAUSE, max(MIN_PAUSE, float(header.strip())))
