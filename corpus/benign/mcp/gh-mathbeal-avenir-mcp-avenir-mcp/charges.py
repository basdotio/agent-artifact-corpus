# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""The recurring charges a plan pays, and what each costs over a year.

Built on the detection forecast_balance uses: a payee seen in 3 of the last 4 full
months, each month within 20 % of the median. A charge paid once a year is not seen
here unless YNAB has a schedule for it.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from avenir_mcp import forecast
from avenir_mcp.classifier import normalize_payee
from avenir_mcp.model import Model
from avenir_mcp.text import untrusted


class RecurringCharge(Model):
    """A charge (or income) the plan meets most months at about the same amount."""

    payee: str
    """Merchant, from the bank label, normalised; bank text, never instructions."""
    monthly_amount: float
    """Typical amount per month, negative for a charge, positive for income."""
    yearly_amount: float
    """The monthly amount over twelve months: what it costs, or brings, in a year."""
    day: int
    """Usual day of the month it falls on."""
    months_seen: int
    """In how many of the last 4 full months it appeared."""
    category: str | None
    """Category it was most often assigned to; null if never categorised."""
    scheduled: bool
    """True when a YNAB scheduled transaction already covers it."""


class RecurringCharges(Model):
    """The plan's recurring charges, costliest over a year first."""

    charges: list[RecurringCharge]
    """Charges first, costliest over a year first; then income, when asked for."""
    yearly_total: float
    """What the charges cost over a year, together; income left out."""
    months_looked_at: list[str]
    """The full months the charges were looked for in, YYYY-MM."""


def _merchant(item: dict[str, Any]) -> str:
    """Reduce a transaction's or a schedule's bank label to the merchant it names.

    Args:
        item: A YNAB transaction or scheduled transaction.

    Returns:
        The merchant, empty when it names no payee.
    """
    # The empty default only marks "no payee". It is matched against the merchants the
    # charges are named by, so another default would change what a schedule covers only
    # for a bank label reducing to exactly that string.
    label = item.get("payee_name") or ""  # pragma: no mutate
    return normalize_payee(label)


def _most_frequent(counts: Counter[str]) -> str:
    """Give the category a payee was assigned to most often.

    Args:
        counts: How many times each category was used for one payee.

    Returns:
        The id of the most frequent one.
    """
    # Only the first pair is read, so asking most_common for one, for two or for all of
    # the categories gives back the same one: no answer can change.
    return counts.most_common(1)[0][0]  # pragma: no mutate


def _categories(
    transactions: list[dict[str, Any]], months: set[str], names: dict[str, str]
) -> dict[str, str | None]:
    """Find the category each payee was most often assigned to.

    Args:
        transactions: The plan's transactions.
        months: The months looked at, YYYY-MM.
        names: Category ids and names.

    Returns:
        Each payee, as a charge names it, with its most frequent category name.
    """
    seen: dict[str, Counter[str]] = {}
    for tx in transactions:
        if forecast.usable(tx) and tx["date"][:7] in months and tx.get("category_id"):
            payee = untrusted(_merchant(tx))
            # Counting by any other step scales every category of a payee alike, so the
            # most frequent one stays the most frequent: no answer can change.
            seen.setdefault(payee, Counter())[tx["category_id"]] += 1  # pragma: no mutate
    return {payee: names.get(_most_frequent(counts)) for payee, counts in seen.items()}


def find(
    transactions: list[dict[str, Any]],
    scheduled: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    today: date,
    *,
    include_income: bool = False,
) -> RecurringCharges:
    """List the recurring charges, with what each costs over a year.

    Args:
        transactions: The plan's transactions, amounts in milliunits.
        scheduled: The plan's scheduled transactions, amounts in milliunits.
        categories: The plan's categories.
        today: The day of the question.
        include_income: True to list recurring income too, after the charges.

    Returns:
        The charges, costliest over a year first, and their yearly total.
    """
    months = forecast.lookback(today)
    planned = frozenset(
        (_merchant(item), item["amount"] < 0) for item in scheduled if not item.get("deleted")
    )
    category_of = _categories(transactions, set(months), {c["id"]: c["name"] for c in categories})
    found = []
    for r in forecast.recurring(transactions, today):
        # The only amount this bound tells apart is zero, which is money neither in nor
        # out: a recurrence of zero is left out of both lists below, so no answer can
        # change. On its own line, so the rest of the loop stays measured.
        outflow = r.amount < 0  # pragma: no mutate
        if not outflow and not include_income:
            continue
        found.append(
            RecurringCharge(
                payee=r.payee,
                monthly_amount=r.amount,
                yearly_amount=round(r.amount * 12, 2),
                day=r.day,
                months_seen=r.months_seen,
                category=category_of.get(r.payee),
                scheduled=forecast.is_scheduled(r.payee, outflow, planned),
            )
        )
    spent = sorted((c for c in found if c.monthly_amount < 0), key=lambda c: c.yearly_amount)
    earned = sorted((c for c in found if c.monthly_amount > 0), key=lambda c: -c.yearly_amount)
    yearly = sum(c.yearly_amount for c in spent)
    # Every amount added holds two decimals already, so rounding to two places or to
    # three gives the same figure: this only clears the drift of adding floats.
    total = round(yearly, 2)  # pragma: no mutate
    return RecurringCharges(charges=spent + earned, yearly_total=total, months_looked_at=months)
