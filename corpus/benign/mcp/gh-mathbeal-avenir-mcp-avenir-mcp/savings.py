# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""How much of the income was kept, month by month.

Income is money in categorised to Ready to Assign on the budget accounts. Spending is
money out of them, less refunds. What is left was saved: kept in the budget accounts,
or moved to a tracking account that holds an asset. Sums are made in milliunits.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from avenir_mcp.client import milliunit_to_amount
from avenir_mcp.forecast import months_before
from avenir_mcp.model import Model
from avenir_mcp.networth import tracking_assets
from avenir_mcp.runway import lines_of

MAX_MONTHS = 24
"""Two years, as get_spending_trends and get_runway."""

INTERNAL_GROUP = "Internal Master Category"
"""YNAB's own group: "Inflow: Ready to Assign", where income goes, and "Uncategorized"."""
UNCATEGORIZED = "Uncategorized"
"""The internal category of a transaction waiting for one: not income."""
STARTING_BALANCE = "Starting Balance"
"""The payee YNAB gives an account's first balance: money already there, not income."""


class SavingsMonth(Model):
    """What came in, went out and was kept in one month, in currency units."""

    month: str
    """The month, YYYY-MM."""
    income: float
    """Money in categorised to Ready to Assign."""
    spending: float
    """Money out less refunds, negative; transfers to an asset tracking account excluded."""
    saved: float
    """Income plus spending: what was kept; negative when more went out than came in."""
    rate: float | None
    """Saved over income, in percent to one decimal; null when nothing came in."""


class SavingsRate(Model):
    """The share of income kept each month, and over the whole period."""

    message: str
    """The conclusion in one sentence or two, for the agent to relay."""
    months: list[SavingsMonth]
    """The complete months measured, oldest first."""
    income: float
    """Income over the period."""
    spending: float
    """Spending over the period, negative."""
    saved: float
    """Saved over the period: income plus spending."""
    rate: float | None
    """Saved over income for the whole period, in percent to one decimal; null when nothing
    came in."""
    average_saved: float
    """Saved per month, on average over the months measured."""
    best_month: str | None
    """The month with the highest rate, YYYY-MM; null when no month had income."""
    worst_month: str | None
    """The month with the lowest rate, YYYY-MM; null when no month had income."""
    moved_to_tracking: float
    """Money moved to tracking accounts that hold an asset over the period, part of saved."""
    notes: list[str]
    """How the figures were counted, to tell the user."""


def _rate(saved: int, income: int) -> float | None:
    """Give saved over income in percent.

    Args:
        saved: Money kept, in milliunits.
        income: Money in, in milliunits.

    Returns:
        The percentage to one decimal, or None when nothing came in.
    """
    return round(saved / income * 100, 1) if income else None


def _notes(months: list[SavingsMonth], asked: int, uncategorized: list[int]) -> list[str]:
    """Write down how the figures were counted.

    Args:
        months: The months measured.
        asked: How many months the caller asked for.
        uncategorized: Amounts of the inflows without a category, in milliunits.

    Returns:
        The notes, one sentence each.
    """
    notes = [
        "Income is money in categorised to Ready to Assign on the budget accounts; starting "
        "balances and transfers, from a tracking account too, are not income.",
        "Spending is money out of the budget accounts less refunds (money in categorised "
        "to a spending category); transfers between budget accounts are left out.",
        "A transfer to a tracking account that holds an asset (savings, investments) is "
        "saved, not spent; a transfer to a tracking loan or debt is spending, as YNAB's "
        "budget counts it.",
        "Saved is income less spending: what stayed in the budget accounts or went to an "
        "asset outside them. The rate is saved over income.",
    ]
    if uncategorized:
        notes.append(
            f"{len(uncategorized)} inflows without a category "
            f"({milliunit_to_amount(sum(uncategorized)):.2f}) are counted neither as income "
            "nor as refunds: categorise them in YNAB for a true figure."
        )
    if months and len(months) < asked:
        notes.append(
            f"Only the last {len(months)} of the {asked} months hold budget transactions: "
            "the figures are over those."
        )
    if empty := [m.month for m in months if m.rate is None]:
        notes.append(f"No rate for {', '.join(empty)}: no income was categorised that month.")
    return notes


def summary(  # pylint: disable=too-many-locals
    accounts: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    today: date,
    months_count: int,
) -> SavingsRate:
    """Say how much of the income was kept in each of the last complete months.

    Args:
        accounts: The plan's accounts not deleted.
        categories: The plan's categories, each with its id, name and group's name.
        transactions: The plan's transactions, amounts in milliunits.
        today: The day of the question; its month is incomplete and not measured.
        months_count: How many complete months, at most; months before the budget's
            first transaction are not measured.

    Returns:
        Income, spending, saved and rate per month and over the period, and the rules.
    """
    budget = {a["id"] for a in accounts if a["on_budget"]}
    assets = tracking_assets(accounts)
    internal = {c["id"] for c in categories if c.get("category_group_name") == INTERNAL_GROUP}
    income_ids = {c["id"] for c in categories if c["id"] in internal and c["name"] != UNCATEGORIZED}

    history = [tx for tx in transactions if tx["account_id"] in budget and not tx.get("deleted")]
    # The sentinel only has to keep every month out when the plan holds no budget
    # transaction at all: any text sorting after a YYYY-MM month does that. On its own
    # line, so the pragma covers no more than the sentinel.
    none_yet = "9999-12"  # pragma: no mutate
    first = min((tx["date"][:7] for tx in history), default=none_yet)
    months = [month for month in months_before(today, months_count) if month >= first]
    income = dict.fromkeys(months, 0)
    spent = dict.fromkeys(months, 0)
    moved = 0
    uncategorized: list[int] = []
    for tx in history:
        month = tx["date"][:7]
        if month not in income:
            continue
        for line in lines_of(tx):
            amount, transfer = line["amount"], line.get("transfer_account_id")
            category = line.get("category_id")
            # Which way the line goes. It is read only once the line is known to move
            # something, since the first test below leaves on a line of zero, so a bound
            # that includes zero, or one at 1, answers the same. On its own line, so the
            # pragma covers no more than this comparison.
            outflow = amount < 0  # pragma: no mutate
            # Nothing moved, money between budget accounts, or back from outside: skipped.
            if not amount or transfer in budget or (transfer and not outflow):
                continue
            if transfer in assets:
                moved -= amount
            elif outflow or (category and category not in internal):
                spent[month] += amount
            elif category not in income_ids:
                uncategorized.append(amount)
            elif tx.get("payee_name") != STARTING_BALANCE:
                income[month] += amount

    rows = [
        SavingsMonth(
            month=month,
            income=milliunit_to_amount(income[month]),
            spending=milliunit_to_amount(spent[month]),
            saved=milliunit_to_amount(income[month] + spent[month]),
            rate=_rate(income[month] + spent[month], income[month]),
        )
        for month in months
    ]
    total_in, total_spent = sum(income.values()), sum(spent.values())
    rated = [row for row in rows if row.rate is not None]
    best = max(rated, key=lambda row: row.rate or 0.0, default=None)
    worst = min(rated, key=lambda row: row.rate or 0.0, default=None)
    rate = _rate(total_in + total_spent, total_in)
    if not months:
        message = "No complete month holds budget transactions yet: no savings rate to give."
    elif rate is None:
        message = (
            f"No income was categorised to Ready to Assign over the last {len(months)} "
            f"complete months: no savings rate can be given; "
            f"{-milliunit_to_amount(total_spent):.2f} was spent."
        )
    else:
        message = (
            f"Over the last {len(months)} complete months, "
            f"{milliunit_to_amount(total_in):.2f} came in and "
            f"{-milliunit_to_amount(total_spent):.2f} went out: "
            f"{milliunit_to_amount(total_in + total_spent):.2f} saved, {rate} % of the income."
        )
        if best is not None and worst is not None and best is not worst:
            message += (
                f" Best month: {best.month} ({best.rate} %), worst: {worst.month} ({worst.rate} %)."
            )
    return SavingsRate(
        message=message,
        months=rows,
        income=milliunit_to_amount(total_in),
        spending=milliunit_to_amount(total_spent),
        saved=milliunit_to_amount(total_in + total_spent),
        rate=rate,
        average_saved=milliunit_to_amount(
            round((total_in + total_spent) / len(months)) if months else 0
        ),
        best_month=best.month if best else None,
        worst_month=worst.month if worst else None,
        moved_to_tracking=milliunit_to_amount(moved),
        notes=_notes(rows, months_count, uncategorized),
    )
