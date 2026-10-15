# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Financial analytics computed from YNAB data — pure functions, no I/O."""

from __future__ import annotations

import logging
from typing import Any

from avenir_mcp import client
from avenir_mcp.model import Model

logger = logging.getLogger(__name__)


class BudgetUsage(Model):
    """How much of a category's budget was used in a month."""

    id: str
    """YNAB id of the category."""
    name: str
    """Category name."""
    group: str
    """Name of the category's group, e.g. Fun for Tennis."""
    budgeted: float
    """Amount assigned to the category this month."""
    actual: float
    """Amount spent this month, as a positive number."""
    balance: float
    """What is left: budgeted minus spent, plus what was carried over; negative when overspent."""
    utilization_pct: float
    """Spent as a share of budgeted, in percent; above 100 means overspent, 0 when nothing
    is budgeted."""


def budget_vs_actual(
    month_categories: list[dict[str, Any]],
) -> list[BudgetUsage]:
    """Compute budget-vs-actual for each category in a given month.

    Args:
        month_categories: List of YNAB category dicts for a specific month,
            each containing ``budgeted`` and ``activity`` in milliunits.

    Returns:
        One usage per usable category, amounts in currency units.

    Examples:
        >>> cat = {"id": "c1", "name": "Rent", "budgeted": 500000,
        ...        "activity": -400000, "balance": 100000}
        >>> budget_vs_actual([cat])[0].utilization_pct
        80.0
    """
    results: list[BudgetUsage] = []
    for cat in filter(_usable, month_categories):
        budgeted_mu = cat.get("budgeted", 0)
        activity_mu = cat.get("activity", 0)
        balance_mu = cat.get("balance", 0)
        budgeted = client.milliunit_to_amount(budgeted_mu)
        actual = client.milliunit_to_amount(abs(activity_mu))
        balance = client.milliunit_to_amount(balance_mu)

        if budgeted_mu == 0:
            utilization_pct = 0.0
        else:
            utilization_pct = round(actual / budgeted * 100, 1)

        results.append(
            BudgetUsage(
                id=cat.get("id", ""),
                name=cat.get("name", ""),
                group=cat.get("category_group_name", ""),
                budgeted=budgeted,
                actual=actual,
                balance=balance,
                utilization_pct=utilization_pct,
            )
        )
    return results


class MonthSpending(Model):
    """What a category spent in one month."""

    month: str
    """First day of the month, YYYY-MM-01."""
    amount: float
    """Amount spent, as a positive number in currency units."""


def spending_trends(
    months_data: list[tuple[str, list[dict[str, Any]]]],
) -> dict[str, list[MonthSpending]]:
    """Build a time-series of spending per category across multiple months.

    Args:
        months_data: List of ``(month_label, month_categories)`` tuples,
            ordered chronologically.  Each element is a ``(str, list)`` pair
            where the string is an ISO month label and the list is the output of
            :func:`client.get_month_categories`.

    Returns:
        Dict mapping category name to its spending, month by month in chronological
        order.

    Examples:
        >>> cats = [{"id": "c1", "name": "AWS", "budgeted": 0, "activity": -100000, "balance": 0}]
        >>> spending_trends([("2026-01-01", cats)])["AWS"]
        [MonthSpending(month='2026-01-01', amount=100.0)]
    """
    trends: dict[str, list[MonthSpending]] = {}
    for month_label, categories in months_data:
        for cat in filter(_usable, categories):
            name = cat.get("name")
            if not name:
                continue
            amount = client.milliunit_to_amount(abs(cat.get("activity", 0)))
            if name not in trends:
                trends[name] = []
            trends[name].append(MonthSpending(month=month_label, amount=amount))
    return trends


class PayeeTotal(Model):
    """What was spent with one payee."""

    payee_name: str
    """Payee name; Unknown when the transactions have none."""
    total: float
    """Total spent, as a positive number in currency units."""
    count: int
    """Number of transactions."""


def top_payees(
    transactions: list[dict[str, Any]],
    limit: int = 10,
) -> list[PayeeTotal]:
    """Aggregate transactions by payee and return the top spenders.

    Args:
        transactions: List of YNAB transaction dicts with ``payee_name``
            and ``amount`` fields (amounts are in milliunits, negative = expense).
        limit: Maximum number of payees to return (default 10).

    Returns:
        The payees, the biggest spending first.

    Examples:
        >>> txs = [
        ...     {"payee_name": "AWS", "amount": -50000},
        ...     {"payee_name": "AWS", "amount": -30000},
        ...     {"payee_name": "Loyer", "amount": -500000},
        ... ]
        >>> top_payees(txs, limit=1)[0].payee_name
        'Loyer'
    """
    totals: dict[str, dict[str, Any]] = {}
    for tx in transactions:
        payee = tx.get("payee_name") or "Unknown"
        amount_mu = tx.get("amount", 0)
        if payee not in totals:
            totals[payee] = {"total_mu": 0, "count": 0}
        totals[payee]["total_mu"] += abs(amount_mu)
        totals[payee]["count"] += 1

    sorted_payees = sorted(totals.items(), key=lambda kv: kv[1]["total_mu"], reverse=True)
    return [
        PayeeTotal(
            payee_name=name,
            total=client.milliunit_to_amount(data["total_mu"]),
            count=data["count"],
        )
        for name, data in sorted_payees[:limit]
    ]


_INTERNAL_GROUP = "Internal Master Category"


class Overspent(Model):
    """A category whose available balance is negative."""

    category_id: str
    """YNAB id of the category."""
    name: str
    """Category name."""
    group: str
    """Name of the category's group."""
    balance: float
    """Available balance, negative: the amount overspent, in currency units."""


class MonthOverview(Model):
    """A month's totals and the categories that need attention."""

    month: str
    """First day of the month, YYYY-MM-01."""
    income: float
    """Money received in the month and assigned to Ready to Assign."""
    budgeted: float
    """Total assigned to categories in the month."""
    activity: float
    """Total spent (negative) and received in categories during the month."""
    ready_to_assign: float
    """Money not yet given a job; negative when more was assigned than received."""
    age_of_money: int | None
    """Days between receiving money and spending it, as YNAB computes it; null when unknown."""
    overspent: list[Overspent]
    """Categories whose available balance is negative this month."""


class CategoryBalance(Model):
    """One category's month in currency units."""

    category_id: str
    """YNAB id of the category."""
    name: str
    """Category name."""
    group: str
    """Name of the category's group."""
    budgeted: float
    """Amount assigned to the category this month."""
    activity: float
    """Amount spent (negative) or received in the category this month."""
    balance: float
    """Available at the end of the month: carried over, plus budgeted, plus activity."""


def _usable(cat: dict[str, Any]) -> bool:
    """Tell whether a category counts as the user's spending.

    Args:
        cat: A YNAB category.

    Returns:
        True when it is visible, not deleted, and not one of YNAB's internal categories.
    """
    return (
        not cat.get("hidden")
        and not cat.get("deleted")
        and cat.get("category_group_name") != _INTERNAL_GROUP
    )


def month_overview(month: dict[str, Any]) -> MonthOverview:
    """Summarise a YNAB month: totals in currency units and overspent categories.

    Args:
        month: A YNAB month, as returned by :func:`client.get_month`.

    Returns:
        The month's totals and the usable categories whose balance is negative.
    """
    amount = client.milliunit_to_amount
    overspent: list[Overspent] = []
    for cat in month.get("categories", []):
        # YNAB gives every category of a month its balance. The default only marks an
        # absence, and a category with nothing left is not overspent either way. On its
        # own line, so the pragma covers no more than this one lookup.
        balance = cat.get("balance", 0)  # pragma: no mutate
        if _usable(cat) and balance < 0:
            overspent.append(
                Overspent(
                    category_id=cat["id"],
                    name=cat["name"],
                    group=cat.get("category_group_name", ""),
                    balance=amount(balance),
                )
            )
    return MonthOverview(
        month=month["month"],
        income=amount(month.get("income", 0)),
        budgeted=amount(month.get("budgeted", 0)),
        activity=amount(month.get("activity", 0)),
        ready_to_assign=amount(month.get("to_be_budgeted", 0)),
        age_of_money=month.get("age_of_money"),
        overspent=overspent,
    )


def category_balances(
    categories: list[dict[str, Any]], include_empty: bool = False
) -> list[CategoryBalance]:
    """Give one line per usable category of a month.

    Args:
        categories: The month's YNAB categories, amounts in milliunits.
        include_empty: Also list categories with nothing budgeted, spent or available.

    Returns:
        Each category's budgeted, activity and balance, in currency units.
    """
    amount = client.milliunit_to_amount
    return [
        CategoryBalance(
            category_id=cat["id"],
            name=cat["name"],
            group=cat.get("category_group_name", ""),
            budgeted=amount(cat.get("budgeted", 0)),
            activity=amount(cat.get("activity", 0)),
            balance=amount(cat.get("balance", 0)),
        )
        for cat in categories
        if _usable(cat)
        and (include_empty or any(cat.get(key) for key in ("budgeted", "activity", "balance")))
    ]
