# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""A category's target: what it is, what a change sends YNAB, and what brings it back.

YNAB's API sets a target through three fields: an amount, then either a date (a
target to reach by then) or a frequency (monthly, weekly, yearly), not both. It keeps
an existing target's kind when only the amount changes. It cannot choose a kind: a
target set in the app as monthly funding, a target balance or a debt payment cannot
be recreated once replaced or removed, and undo says so before the user confirms.

Two kinds of category take fewer targets. A credit card payment category takes no
frequency, and an amount alone gives it monthly funding. A category paired to a loan
account takes neither a date nor a frequency. The API does not say which categories
are paired to a loan: one is recognised by its debt payment target, and one without a
target yet is refused by YNAB itself, after the user confirms.
"""

from __future__ import annotations

from typing import Any, Literal

from avenir_mcp.client import amount_to_milliunit
from avenir_mcp.model import Model
from avenir_mcp.triage import CARD_GROUP

Frequency = Literal["monthly", "weekly", "yearly"]
_CADENCE: dict[int, str] = {1: "monthly", 2: "weekly", 13: "yearly"}
_RHYTHM = {"monthly": "each month", "weekly": "each week", "yearly": "each year"}
_KIND = {
    "MF": "monthly funding",
    "TB": "target balance",
    "TBD": "target balance by date",
    "DEBT": "debt payment",
    "NEED": "spending target",
}


_CARD = "a credit card payment category"
_LOAN = "a category paired to a loan account"


class TargetPlan(Model):
    """A change of target, before it is sent."""

    fields: dict[str, Any]
    """What the change sends YNAB, amounts in milliunits."""
    undo: dict[str, Any] | None
    """What brings the previous target back; null when YNAB's API cannot recreate it."""
    before: str
    """The target before, as the user reads it."""
    after: str
    """The target after, as the user reads it."""
    unchanged: bool
    """True when the target asked for is the one already set."""


def _frequency(category: dict[str, Any]) -> str | None:
    """The rhythm of a spending target the API can set again, or None.

    Args:
        category: A category as YNAB returns it.

    Returns:
        monthly, weekly or yearly, or None for any other cadence.
    """
    if category.get("goal_cadence_frequency") not in (None, 1):
        return None
    return _CADENCE.get(category.get("goal_cadence") or 0)


def describe(category: dict[str, Any]) -> str:
    """Say a category's target as the user reads it.

    Args:
        category: A category as YNAB returns it, amounts in milliunits.

    Returns:
        "no target", "50.00 each month", "1200.00 by 2027-06-01", or the amount with the
        YNAB kind when it is one the API cannot set.
    """
    kind, target = category.get("goal_type"), category.get("goal_target")
    if kind is None or target is None:
        return "no target"
    amount = f"{target / 1000:.2f}"
    date = category.get("goal_target_date")
    if kind == "NEED" and date:
        return f"{amount} by {date}"
    if kind == "NEED" and (rhythm := _frequency(category)):
        return f"{amount} {_RHYTHM[rhythm]}"
    return f"{amount} ({_KIND.get(kind, kind)})"


def recreate(category: dict[str, Any]) -> dict[str, Any] | None:
    """Find the fields that set a category's current target again.

    Args:
        category: A category as YNAB returns it.

    Returns:
        The fields, or None when YNAB's API cannot recreate this target.
    """
    kind, target = category.get("goal_type"), category.get("goal_target")
    if kind is None or target is None:
        return {"goal_target": None}
    if kind != "NEED":
        return None
    whole = {"goal_needs_whole_amount": bool(category.get("goal_needs_whole_amount"))}
    if category.get("goal_target_date"):
        return {"goal_target": target, "goal_target_date": category["goal_target_date"]} | whole
    rhythm = _frequency(category)
    return {"goal_target": target, "goal_frequency": rhythm} | whole if rhythm else None


def _paired(category: dict[str, Any]) -> str | None:
    """Say which kind of category takes fewer targets, if this is one.

    Args:
        category: A category as YNAB returns it.

    Returns:
        The kind, as the user reads it, or None for an ordinary category.
    """
    if category.get("category_group_name") == CARD_GROUP:
        return _CARD
    if category.get("goal_type") == "DEBT":
        return _LOAN
    return None


def _check(
    amount: float | None, date: str | None, frequency: str | None, paired: str | None
) -> None:
    """Refuse what YNAB would refuse.

    Args:
        amount: The target amount, or None to remove the target.
        date: The date to reach it by, or None.
        frequency: monthly, weekly or yearly, or None.
        paired: The kind of category that takes fewer targets, or None.

    Raises:
        ValueError: If both a date and a frequency are given, a removal carries either,
            the amount is not positive, or the category does not take the rhythm asked.
    """
    if date and frequency:
        raise ValueError("Give either a date or a frequency, not both: YNAB refuses the two.")
    if amount is None and (date or frequency):
        raise ValueError("To remove the target, give no amount, no date and no frequency.")
    if amount is not None and amount <= 0:
        raise ValueError("The amount must be greater than 0; to remove the target, give none.")
    if paired == _LOAN and (date or frequency):
        raise ValueError(
            f"YNAB takes neither a date nor a frequency on {_LOAN}: give an amount alone."
        )
    if paired == _CARD and frequency:
        raise ValueError(f"YNAB takes no frequency on {_CARD}: give an amount alone, or a date.")


def plan(
    category: dict[str, Any],
    *,
    amount: float | None,
    date: str | None,
    frequency: str | None,
) -> TargetPlan:
    """Work out a change of target, and how to undo it.

    Args:
        category: The category as YNAB returns it, amounts in milliunits.
        amount: The target amount in currency units, or None to remove the target.
        date: YYYY-MM-DD to reach the amount by, or None.
        frequency: monthly, weekly or yearly, or None.

    Returns:
        What to send, what brings the previous target back, and both as the user reads them.

    Raises:
        ValueError: If the change is one YNAB would refuse.
    """
    paired = _paired(category)
    _check(amount, date, frequency, paired)
    had = category.get("goal_type") is not None and category.get("goal_target") is not None
    if amount is None:
        fields: dict[str, Any] = {"goal_target": None}
        # Only describe() reads this one, and it reads both fields as missing whatever
        # they are called here: a target removed has nothing left to describe.
        after: dict[str, Any] = {"goal_type": None, "goal_target": None}  # pragma: no mutate
    else:
        milli = amount_to_milliunit(amount)
        fields = {"goal_target": milli}
        if date:
            fields["goal_target_date"] = date
            after = {"goal_type": "NEED", "goal_target": milli, "goal_target_date": date}
        elif frequency:
            fields["goal_frequency"] = frequency
            cadence = {v: k for k, v in _CADENCE.items()}[frequency]
            after = {"goal_type": "NEED", "goal_target": milli, "goal_cadence": cadence}
        elif had:
            after = category | {"goal_target": milli}
        elif paired == _CARD:
            after = {"goal_type": "MF", "goal_target": milli}
        else:
            after = {"goal_type": "NEED", "goal_target": milli, "goal_cadence": 1}
    amount_only = amount is not None and not date and not frequency and had
    undo = {"goal_target": category["goal_target"]} if amount_only else recreate(category)
    return TargetPlan(
        fields=fields,
        undo=undo,
        before=describe(category),
        after=describe(after),
        unchanged=describe(after) == describe(category),
    )
