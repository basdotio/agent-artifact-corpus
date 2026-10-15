# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""How many months the money available would last at the usual pace of spending.

The money available is today's balance of the budget's checking, savings and cash
accounts, less what its cards owe. The pace is the average money out of the budget
accounts over the last complete months. No income is assumed. Sums are made in
milliunits.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from avenir_mcp.client import amount_to_milliunit, milliunit_to_amount
from avenir_mcp.forecast import months_before
from avenir_mcp.model import Model
from avenir_mcp.networth import tracking_assets
from avenir_mcp.text import untrusted

MAX_MONTHS = 24
"""Two years, as get_spending_trends: older months say little about today's pace."""

CASH_TYPES = frozenset({"checking", "savings", "cash"})
"""Budget account types whose balance is money to live on."""
CARD_TYPES = frozenset({"creditCard", "lineOfCredit"})
"""Budget account types whose balance is owed: it will have to be paid."""


class RunwayAccount(Model):
    """A budget account counted in the money available."""

    name: str
    """Account name, as the user wrote it in YNAB."""
    type: str
    """YNAB account type: checking, savings, cash, creditCard or lineOfCredit."""
    balance: float
    """Balance today in currency units; a card's is negative while money is owed."""


class Coverage(Model):
    """A pace of spending, and how long the money available would last at it."""

    monthly_spending: float
    """Average money out per month over the months used, in currency units, negative."""
    runway_months: float | None
    """Money available over monthly spending, to one decimal; 0 when nothing is available;
    null when nothing was spent, or no month could be averaged: no end can be given."""


class Runway(Model):
    """How many months the money available would last without income."""

    message: str
    """The conclusion in one sentence or two, for the agent to relay."""
    liquid: float
    """Money available today: the counted accounts' balances, cards' debts subtracted."""
    owed_on_cards: float
    """What the budget's credit cards and lines of credit add up to, already in liquid;
    negative while money is owed."""
    spending: Coverage
    """All spending."""
    essential: Coverage | None
    """Spending in the essential groups only; null when none were given."""
    essential_groups: list[str]
    """Names of the category groups counted as essential."""
    months: list[str]
    """The complete months averaged, YYYY-MM, oldest first."""
    accounts: list[RunwayAccount]
    """The accounts counted in the money available."""
    left_out: list[str]
    """Names of the open accounts not counted: tracking accounts (investments, loans),
    and savings when asked to leave them out."""
    notes: list[str]
    """What the figures assume, to tell the user."""


def chosen_groups(groups: list[dict[str, Any]], wanted: list[str]) -> list[dict[str, Any]]:
    """Find the category groups the caller named, by id or by name whatever the case.

    Args:
        groups: The plan's groups, each with its id, name and category_ids.
        wanted: Group names or ids, as the caller gave them.

    Returns:
        The groups named, in the order given, each once.

    Raises:
        ValueError: If a name or id is not one of the plan's groups, with the groups
            it could be.
    """
    by_id = {group["id"]: group for group in groups}
    found: list[dict[str, Any]] = []
    unknown: list[str] = []
    for item in wanted:
        key = item.strip()
        matches = (
            [by_id[key]]
            if key in by_id
            else [g for g in groups if g["name"].strip().casefold() == key.casefold()]
        )
        if not matches:
            unknown.append(item)
        found += [group for group in matches if group not in found]
    if unknown:
        given = ", ".join(repr(untrusted(name)) for name in unknown)
        names = ", ".join(untrusted(group["name"]) for group in groups)
        raise ValueError(
            f"Unknown category group(s) {given}: give names or ids of this plan's groups, "
            f"as list_category_groups shows them: {names}."
        )
    return found


def lines_of(tx: dict[str, Any]) -> list[dict[str, Any]]:
    """Give the lines of a transaction: its split lines, or itself when not split.

    Args:
        tx: A YNAB transaction.

    Returns:
        The split lines not deleted, or the transaction alone.
    """
    split = [line for line in tx.get("subtransactions") or [] if not line.get("deleted")]
    return split or [tx]


def _coverage(liquid: int, spent: int, months: int) -> Coverage:
    """Average a spending total over the months, and see how long the money lasts.

    Args:
        liquid: Money available, in milliunits.
        spent: Money out over the months, in milliunits, negative.
        months: How many months; 0 when none could be averaged.

    Returns:
        The monthly average and the runway in months.
    """
    average = round(spent / months) if months else 0
    # Owing more than the money available is no runway at all, not a negative one.
    runway = None if not average else max(round(liquid / -average, 1), 0.0)
    return Coverage(monthly_spending=milliunit_to_amount(average), runway_months=runway)


def _lasts(coverage: Coverage) -> str:
    """Say how long the money lasts, for the message.

    Args:
        coverage: A pace of spending and its runway.

    Returns:
        "2.8 months", or why no end can be given.
    """
    if coverage.runway_months is None:
        return "with no end in sight, since nothing was spent"
    return f"{coverage.runway_months} months"


def _notes(  # pylint: disable=too-many-arguments
    *,
    months: list[str],
    asked: int,
    liquid: int,
    owed: int,
    cards: bool,
    include_savings: bool,
) -> list[str]:
    """Write down what the figures assume.

    Args:
        months: The months averaged.
        asked: How many months the caller asked for.
        liquid: Money available, in milliunits.
        owed: What the cards owe, in milliunits.
        cards: True when the budget has a card or line of credit.
        include_savings: False when savings accounts were left out.

    Returns:
        The notes, one sentence each.
    """
    notes = [
        "No income is assumed: the runway is how long the money would last if nothing came in.",
        "Spending is the past average of money out of the budget accounts; refunds and "
        "other money in are not deducted, transfers between budget accounts are left out, "
        "and transfers to a tracking loan or debt (a loan payment, say) count as spending.",
        "A transfer to a tracking account that holds an asset (savings, investments) is not "
        "spending: that money is still yours, as get_savings_rate counts it.",
        "Tracking accounts are not counted as money available: investments and loans "
        "outside the budget are listed in left_out.",
        "The past is no promise: yearly bills, holidays or a job search change the pace.",
    ]
    if cards:
        notes.append(
            f"What the credit cards owe ({milliunit_to_amount(owed):.2f}) is subtracted "
            "from the money available: it will have to be paid."
        )
    if not include_savings:
        notes.append("Savings accounts were left out of the money available, as asked.")
    if months and len(months) < asked:
        notes.append(
            f"Only the last {len(months)} of the {asked} months hold budget transactions: "
            "the average is over those."
        )
    if liquid <= 0:
        notes.append("The money available is zero or less: nothing to live on without income.")
    return notes


def summary(  # pylint: disable=too-many-arguments,too-many-locals
    accounts: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    today: date,
    months_count: int,
    *,
    essential: list[dict[str, Any]] | None = None,
    include_savings: bool = True,
) -> Runway:
    """Say how many months the money available would last at the usual spending.

    Args:
        accounts: The plan's accounts not deleted, balances in currency units.
        transactions: The plan's transactions, amounts in milliunits.
        today: The day of the question; its month is incomplete and not averaged.
        months_count: How many complete months to average, at most; months before the
            budget's first transaction are not.
        essential: Category groups whose spending is essential, each with its name and
            category_ids; None to leave essential spending out.
        include_savings: False to leave savings accounts out of the money available.

    Returns:
        The money available, the pace of spending, the runway and its assumptions.
    """
    budget = {a["id"] for a in accounts if a["on_budget"]}
    kinds = (CASH_TYPES if include_savings else CASH_TYPES - {"savings"}) | CARD_TYPES
    counted = [a for a in accounts if a["id"] in budget and not a["closed"] and a["type"] in kinds]
    liquid = sum(amount_to_milliunit(a["balance"]) for a in counted)
    owed = sum(amount_to_milliunit(a["balance"]) for a in counted if a["type"] in CARD_TYPES)

    history = [tx for tx in transactions if tx["account_id"] in budget and not tx.get("deleted")]
    # Money moved to another budget account, or to an asset outside it, is not spent.
    kept = budget | tracking_assets(accounts)
    # The sentinel only has to keep every month out when the plan holds no budget
    # transaction at all: any text sorting after a YYYY-MM month does that. On its own
    # line, so the pragma covers no more than the sentinel.
    none_yet = "9999-12"  # pragma: no mutate
    first = min((tx["date"][:7] for tx in history), default=none_yet)
    months = [month for month in months_before(today, months_count) if month >= first]
    vital_ids = {cat_id for group in essential or [] for cat_id in group["category_ids"]}
    spent = vital = 0
    for tx in history:
        if tx["date"][:7] not in months:
            continue
        for line in lines_of(tx):
            # Which way the line goes. A line of zero adds nothing to either total, so a
            # bound that takes it for spending, or one at 1, answers the same. On its own
            # line, so the pragma covers no more than this comparison.
            outflow = line["amount"] < 0  # pragma: no mutate
            if not outflow or line.get("transfer_account_id") in kept:
                continue
            spent += line["amount"]
            if line.get("category_id") in vital_ids:
                vital += line["amount"]

    spending = _coverage(liquid, spent, len(months))
    vital_coverage = None if essential is None else _coverage(liquid, vital, len(months))
    available = f"{milliunit_to_amount(liquid):.2f}"
    if not months:
        message = (
            f"No complete month of spending to average yet: no runway can be given for the "
            f"{available} available."
        )
    else:
        message = (
            f"At the average spending of the last {len(months)} complete months, "
            f"{-spending.monthly_spending:.2f} a month, the {available} available would last "
            f"{_lasts(spending)}."
        )
        if vital_coverage is not None:
            message += (
                f" On essential spending alone, {-vital_coverage.monthly_spending:.2f} a month: "
                f"{_lasts(vital_coverage)}."
            )
    return Runway(
        message=message,
        liquid=milliunit_to_amount(liquid),
        owed_on_cards=milliunit_to_amount(owed),
        spending=spending,
        essential=vital_coverage,
        essential_groups=[untrusted(group["name"]) for group in essential or []],
        months=months,
        accounts=[
            RunwayAccount(name=untrusted(a["name"]), type=a["type"], balance=a["balance"])
            for a in counted
        ],
        left_out=[untrusted(a["name"]) for a in accounts if not a["closed"] and a not in counted],
        notes=_notes(
            months=months,
            asked=months_count,
            liquid=liquid,
            owed=owed,
            cards=any(a["type"] in CARD_TYPES for a in counted),
            include_savings=include_savings,
        ),
    )
