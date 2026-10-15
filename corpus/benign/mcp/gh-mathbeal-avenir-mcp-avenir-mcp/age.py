# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""YNAB's Age of Money, month by month.

YNAB computes the figure and gives it with each month: how many days, on average, passed
between money coming into the budget accounts and being spent. This module reads it; it
does not compute it again, so the answer is the figure the user sees in YNAB.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from avenir_mcp.model import Model

MAX_MONTHS = 24
"""Two years, as get_spending_trends and get_savings_rate."""

A_MONTH = 30
"""Money older than this was received last month or before: YNAB's goal."""


class AgeMonth(Model):
    """YNAB's Age of Money for one month."""

    month: str
    """The month, YYYY-MM."""
    days: int | None
    """The age of the money spent, in days; null when YNAB had not enough history."""
    change: int | None
    """Days gained (positive) or lost since the month before; null when either is unknown."""


class AgeOfMoney(Model):
    """How old the money spent is today, and how that changed month by month."""

    message: str
    """The conclusion in one sentence or two, for the agent to relay."""
    days: int | None
    """The latest Age of Money, in days; null when YNAB gives none."""
    as_of: str | None
    """The month of that figure, YYYY-MM: the current one unless YNAB has none for it."""
    months: list[AgeMonth]
    """The months up to the current one, oldest first."""
    change: int | None
    """Days gained (positive) or lost from the first month with a figure to the latest; null
    with fewer than two figures."""
    trend: Literal["up", "down", "steady"] | None
    """The direction of that change; null with fewer than two figures."""
    notes: list[str]
    """How YNAB counts, and what is missing, to tell the user."""


def _meaning(days: int) -> str:
    """Say in plain words what an Age of Money means.

    Args:
        days: The Age of Money, in days.

    Returns:
        One sentence.
    """
    if days >= A_MONTH:
        return (
            f"Over {A_MONTH} days: you are living on last month's income, the buffer YNAB aims for."
        )
    return (
        f"Under {A_MONTH} days: money is spent within a month of coming in; the older it "
        "gets, the bigger the buffer between pay and bills."
    )


def _notes(rows: list[AgeMonth], asked: int, current: str) -> list[str]:
    """Write down how YNAB counts and what is missing.

    Args:
        rows: The months shown.
        asked: How many months the caller asked for.
        current: The current month, YYYY-MM.

    Returns:
        The notes, one sentence each.
    """
    notes = [
        "Age of Money is YNAB's own figure: for the latest payments out of the budget "
        "accounts, how many days passed since that money came in, the oldest money spent "
        "first, averaged.",
        "The current month's figure moves with each payment; a past month's is the one YNAB "
        "keeps for it.",
    ]
    if empty := [row.month for row in rows if row.days is None]:
        notes.append(
            f"No figure for {', '.join(empty)}: YNAB did not have enough history of money "
            "in and out yet."
        )
    if rows and len(rows) < asked:
        notes.append(f"YNAB holds only {len(rows)} months up to {current}: all are shown.")
    if rows and rows[-1].month != current:
        notes.append(f"YNAB has no month {current} yet: the latest is {rows[-1].month}.")
    return notes


def _rows(months: list[dict[str, Any]], current: str, months_count: int) -> list[AgeMonth]:
    """Keep the last months up to the current one, each with its change.

    Args:
        months: The plan's months as YNAB lists them.
        current: The current month, YYYY-MM; later months are left out.
        months_count: How many months, at most.

    Returns:
        The months kept, oldest first.
    """
    held = sorted(
        (m for m in months if not m.get("deleted") and m["month"][:7] <= current),
        key=lambda m: str(m["month"]),
    )[-months_count:]
    rows: list[AgeMonth] = []
    for month in held:
        days = month.get("age_of_money")
        before = rows[-1].days if rows else None
        change = days - before if days is not None and before is not None else None
        rows.append(AgeMonth(month=month["month"][:7], days=days, change=change))
    return rows


def _message(rows: list[AgeMonth], known: list[tuple[str, int]], current: str) -> str:
    """Write the conclusion: the latest figure, what it means, and how it moved.

    Args:
        rows: The months shown.
        known: The months with a figure, as (month, days), oldest first.
        current: The current month, YYYY-MM.

    Returns:
        One sentence or a few.
    """
    if not rows:
        return f"YNAB returned no month up to {current}: no Age of Money to give."
    if not known:
        return (
            f"YNAB gives no Age of Money for the last {len(rows)} months: it shows one once "
            "the plan has enough history of money in and out."
        )
    (since, first), (as_of, latest) = known[0], known[-1]
    message = (
        f"Your money is {latest} days old ({as_of}, YNAB's Age of Money): what you spend "
        f"came in {latest} days before, on average. " + _meaning(latest)
    )
    if len(known) == 1:
        return message
    if latest == first:
        return message + f" It is unchanged since {since}."
    # Equal figures returned above, so asking for greater and for greater or equal is
    # the same question here. On its own line, so the words below stay measured.
    rose = latest > first  # pragma: no mutate
    direction = "up" if rose else "down"
    return message + f" It went {direction} by {abs(latest - first)} days since {since}."


def summary(months: list[dict[str, Any]], today: date, months_count: int) -> AgeOfMoney:
    """Give YNAB's Age of Money for the last months up to today's, and its trend.

    Args:
        months: The plan's months as YNAB lists them, each with its age_of_money.
        today: The day of the question; months after its month are left out.
        months_count: How many months, at most, the current one included.

    Returns:
        Each month's figure, the latest, the change over the period, and the notes.
    """
    current = f"{today:%Y-%m}"
    rows = _rows(months, current, months_count)
    known = [(row.month, row.days) for row in rows if row.days is not None]
    change = known[-1][1] - known[0][1] if len(known) > 1 else None
    trend: Literal["up", "down", "steady"] | None = None
    if change is not None:
        trend = "up" if change > 0 else "down" if change < 0 else "steady"
    return AgeOfMoney(
        message=_message(rows, known, current),
        days=known[-1][1] if known else None,
        as_of=known[-1][0] if known else None,
        months=rows,
        change=change,
        trend=trend,
        notes=_notes(rows, months_count, current),
    )
