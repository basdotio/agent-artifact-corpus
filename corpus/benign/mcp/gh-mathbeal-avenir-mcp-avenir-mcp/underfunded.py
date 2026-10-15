# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""The targets short of money in a month, the most urgent first.

YNAB computes each target's figures for the month asked: what it still needs this
month to stay on track (Underfunded in YNAB's app), what it needs over its whole
period, how far along it is. Nothing is recomputed here: the figures are sorted,
added up and set against the month's Ready to Assign. Sums are made in milliunits.
"""

from __future__ import annotations

from typing import Any, Literal

from avenir_mcp.client import milliunit_to_amount
from avenir_mcp.model import Model
from avenir_mcp.targets import describe
from avenir_mcp.text import untrusted

Urgency = Literal["due_date", "repeating", "other"]
_ORDER: dict[str, int] = {"due_date": 0, "repeating": 1, "other": 2}
_EVERY_MONTH_OR_WEEK = {1, 2}
"""YNAB's goal_cadence for a target repeated monthly or weekly."""
_REPEATING_KINDS = {"MF", "DEBT"}
"""Monthly funding and debt payments: an amount every month."""


class UnderfundedTarget(Model):
    """A category whose target still needs money this month, in currency units."""

    category_id: str
    """YNAB id of the category."""
    name: str
    """Category name."""
    group: str
    """Name of the category's group."""
    target: str
    """The target as the user reads it, e.g. "450.00 each month" or "250.00 by 2026-10-01"."""
    due: str | None
    """The date the target is due, YYYY-MM-DD; null when it has none."""
    needed: float
    """What the category still needs this month to stay on track, as YNAB counts it."""
    left: float
    """What the target still needs over its whole period, this month included."""
    percent_complete: int | None
    """How far along the target is, in percent, as YNAB counts it; null when unknown."""
    months_left: int | None
    """Months left to fund it, this month included; null when YNAB gives none."""
    urgency: Urgency
    """Why it comes where it does: due_date (a target due by a date), repeating (monthly
    or weekly funding, a debt payment), other (a balance to reach with no date)."""


class UnderfundedTargets(Model):
    """The month's underfunded targets, and whether Ready to Assign covers them."""

    message: str
    """The conclusion in one sentence or two, for the agent to relay."""
    month: str
    """The month, YYYY-MM-01."""
    targets: list[UnderfundedTarget]
    """The targets short this month, the most urgent first, up to the limit."""
    more: int
    """Underfunded targets beyond the limit, not listed; the totals count them."""
    needed: float
    """What every underfunded target needs this month, together."""
    ready_to_assign: float
    """The month's Ready to Assign; negative when more was assigned than received."""
    enough: bool
    """True when Ready to Assign covers everything needed."""
    covered: float
    """What Ready to Assign can cover of what is needed."""
    short_by: float
    """What is needed beyond Ready to Assign; 0 when it is enough."""
    on_track: int
    """Targets that need nothing more this month."""
    notes: list[str]
    """How the figures were counted, to tell the user."""


def _urgency(category: dict[str, Any]) -> Urgency:
    """Say which group of urgency a target belongs to.

    Args:
        category: A category with a target, as YNAB returns it.

    Returns:
        repeating for monthly or weekly funding and debt payments, due_date for any
        other target with a date, other for the rest.
    """
    if (
        category.get("goal_type") in _REPEATING_KINDS
        or category.get("goal_cadence") in _EVERY_MONTH_OR_WEEK
    ):
        return "repeating"
    return "due_date" if category.get("goal_target_date") else "other"


def _line(category: dict[str, Any]) -> UnderfundedTarget:
    """Turn a category with an underfunded target into a line of the answer.

    Args:
        category: The category as YNAB returns it for the month, amounts in milliunits;
            its goal_under_funded is what still falls short, so it is there and above zero.

    Returns:
        The line, names made safe to show.
    """
    return UnderfundedTarget(
        category_id=category["id"],
        name=untrusted(category["name"]),
        group=untrusted(category.get("category_group_name")),
        target=describe(category),
        due=category.get("goal_target_date"),
        needed=milliunit_to_amount(category["goal_under_funded"]),
        left=milliunit_to_amount(category.get("goal_overall_left") or 0),
        percent_complete=category.get("goal_percentage_complete"),
        months_left=category.get("goal_months_to_budget"),
        urgency=_urgency(category),
    )


def _key(line: UnderfundedTarget) -> tuple[int, str, float, str]:
    """Sort the most urgent first.

    Args:
        line: An underfunded target.

    Returns:
        Its group, then its date (dated targets only), then the largest need first,
        then its name.
    """
    # A target with no date to sort on is padded, and that pad is only ever compared with
    # the same pad: a target sorts on its date in the due_date group alone, where YNAB
    # gives every target one. On its own line, so the pragma covers no more than the pad.
    no_date = ""  # pragma: no mutate
    due = line.due if line.urgency == "due_date" and line.due else no_date
    return _ORDER[line.urgency], due, -line.needed, line.name


def _message(  # pylint: disable=too-many-arguments
    month: str, *, count: int, needed: int, ready: int, covered: int, on_track: int
) -> str:
    """Say what the targets need and whether Ready to Assign covers it.

    Args:
        month: The month, YYYY-MM.
        count: How many targets are underfunded.
        needed: What they need together, in milliunits.
        ready: The month's Ready to Assign, in milliunits.
        covered: What Ready to Assign covers of what is needed, in milliunits.
        on_track: How many targets need nothing more.

    Returns:
        The message.
    """
    if not count and not on_track:
        return f"No visible category has a target in {month}."
    if not count:
        noun = "target" if on_track == 1 else "targets"
        verb = "is" if on_track == 1 else "are"
        return f"The {on_track} {noun} of {month} {verb} funded: nothing more is needed this month."
    amount = milliunit_to_amount
    head = (
        f"{count} {'target needs' if count == 1 else 'targets need'} {amount(needed):.2f} in "
        f"{month}; Ready to Assign holds {amount(ready):.2f}: "
    )
    if ready >= needed:
        return head + f"enough for all of them, with {amount(ready - needed):.2f} left."
    return (
        head + f"it covers {amount(covered):.2f} of the {amount(needed):.2f}, "
        f"{amount(needed - covered):.2f} short."
    )


def summary(month: dict[str, Any], limit: int | None) -> UnderfundedTargets:
    """Say which targets are short this month, the most urgent first, and what they need.

    Args:
        month: A YNAB month, as client.get_month returns it, amounts in milliunits.
        limit: How many underfunded targets to list at most; None lists them all.

    Returns:
        The underfunded targets, their total, and how much of it Ready to Assign covers.
    """
    visible = [
        c
        for c in month.get("categories", [])
        if not c.get("hidden") and not c.get("deleted") and c.get("goal_type")
    ]
    snoozed = [c for c in visible if c.get("goal_snoozed_at")]
    active = [c for c in visible if not c.get("goal_snoozed_at")]
    behind = [c for c in active if (c.get("goal_under_funded") or 0) > 0]
    short = sorted(map(_line, behind), key=_key)
    needed = sum(c["goal_under_funded"] for c in behind)
    ready = month.get("to_be_budgeted") or 0
    covered = min(max(ready, 0), needed)
    on_track = len(active) - len(short)
    shown = short[:limit]
    notes = [
        "needed is what YNAB says each category still needs this month to stay on track "
        "(Underfunded in its app); left is what the target needs over its whole period.",
        "Most urgent first: targets due by a date, the soonest first; then monthly and "
        "weekly funding and debt payments; then the rest; the largest need first in each.",
    ]
    if len(short) > len(shown):
        notes.append(
            f"{len(short) - len(shown)} more underfunded targets are not listed; the totals "
            "count them."
        )
    if snoozed:
        names = ", ".join(untrusted(c["name"]) for c in snoozed)
        notes.append(
            f"Targets snoozed in YNAB ask for nothing this month and are left out: {names}."
        )
    return UnderfundedTargets(
        message=_message(
            month["month"][:7],
            count=len(short),
            needed=needed,
            ready=ready,
            covered=covered,
            on_track=on_track,
        ),
        month=month["month"],
        targets=shown,
        more=len(short) - len(shown),
        needed=milliunit_to_amount(needed),
        ready_to_assign=milliunit_to_amount(ready),
        enough=ready >= needed,
        covered=milliunit_to_amount(covered),
        short_by=milliunit_to_amount(needed - covered),
        on_track=on_track,
        notes=notes,
    )
