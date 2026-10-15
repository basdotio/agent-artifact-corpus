# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""What a plan owns and owes at the end of each month, rebuilt from today's balances.

YNAB gives each account's balance today, not at a past date. The balance at the end
of a month is today's, less every transaction dated after that month: the same
transactions YNAB adds up, so the figures agree with the registers.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from avenir_mcp.client import amount_to_milliunit, milliunit_to_amount
from avenir_mcp.model import Model

MAX_MONTHS = 24
"""Two years, as get_spending_trends: the answer stays short enough to read."""

DEBT_TYPES = frozenset(
    {
        "creditCard",
        "lineOfCredit",
        "otherLiability",
        "mortgage",
        "autoLoan",
        "studentLoan",
        "personalLoan",
        "medicalDebt",
        "otherDebt",
    }
)
"""YNAB account types that hold money owed; every other type holds an asset."""


def tracking_assets(accounts: list[dict[str, Any]]) -> set[str]:
    """Find the tracking accounts that hold an asset: savings, investments, a house.

    Money moved there from the budget is still the household's: it is saved, not spent.

    Args:
        accounts: The plan's accounts not deleted.

    Returns:
        The ids of the accounts off the budget whose type is not a debt.
    """
    return {a["id"] for a in accounts if not a["on_budget"] and a["type"] not in DEBT_TYPES}


class NetWorthMonth(Model):
    """What the plan's accounts held at the end of one month, in currency units."""

    month: str
    """The month, YYYY-MM-01; its figures are those of its last day, today for this month."""
    assets: float
    """Balance of the asset accounts: checking, savings, cash, other assets."""
    debts: float
    """Balance of the debt accounts (cards, loans, mortgages), negative while money is owed."""
    net_worth: float
    """Assets plus debts: what would be left if every debt were paid."""


class NetWorthTrend(Model):
    """Net worth month by month, and how it changed."""

    months: list[NetWorthMonth]
    """One entry per month, oldest first."""
    first_net_worth: float
    """Net worth at the end of the first month shown."""
    last_net_worth: float
    """Net worth at the end of the last month shown: today's."""
    change: float
    """Last minus first: positive when the net worth grew."""
    accounts: list[str]
    """Names of the accounts counted: the open ones, and the closed ones that still had a
    balance at one of these month ends."""


def _month_starts(today: date, count: int) -> list[date]:
    """List the first day of the last months, today's included.

    Args:
        today: The day of the question.
        count: How many months.

    Returns:
        The first day of each month, oldest first.
    """
    index = today.year * 12 + today.month - 1
    return [date(i // 12, i % 12 + 1, 1) for i in range(index - count + 1, index + 1)]


def _after(start: date) -> str:
    """Give the first day after a month, to compare with transaction dates.

    Args:
        start: The first day of the month.

    Returns:
        The first day of the next month, YYYY-MM-DD.
    """
    index = start.year * 12 + start.month
    return date(index // 12, index % 12 + 1, 1).isoformat()


def _held(
    accounts: list[dict[str, Any]], transactions: list[dict[str, Any]], bounds: list[str]
) -> dict[str, list[int]]:
    """Rebuild each account's balance at the end of each month.

    Args:
        accounts: The plan's accounts not deleted, balances in currency units.
        transactions: The plan's transactions, amounts in milliunits.
        bounds: The first day after each month, YYYY-MM-DD, oldest first.

    Returns:
        Per account id, its balance in milliunits at the end of each month.
    """
    # Per account, what came in or went out after the end of each month.
    later = {a["id"]: [0] * len(bounds) for a in accounts}
    for tx in transactions:
        moved = later.get(tx["account_id"])
        if moved is None or tx.get("deleted"):
            continue
        for index, bound in enumerate(bounds):
            if tx["date"] >= bound:
                moved[index] += tx["amount"]
    return {
        a["id"]: [amount_to_milliunit(a["balance"]) - out for out in later[a["id"]]]
        for a in accounts
    }


def trend(
    accounts: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    today: date,
    months_count: int,
) -> NetWorthTrend:
    """Rebuild assets, debts and net worth at the end of each of the last months.

    Args:
        accounts: The plan's accounts not deleted, balances in currency units.
        transactions: The plan's transactions, amounts in milliunits.
        today: The day of the question; its month is the last one.
        months_count: How many months, the current one included.

    Returns:
        The months, oldest first, and how the net worth changed over them.
    """
    starts = _month_starts(today, months_count)
    held = _held(accounts, transactions, [_after(start) for start in starts])
    months, net = [], []
    for index, start in enumerate(starts):
        assets = sum(held[a["id"]][index] for a in accounts if a["type"] not in DEBT_TYPES)
        debts = sum(held[a["id"]][index] for a in accounts if a["type"] in DEBT_TYPES)
        net.append(assets + debts)
        months.append(
            NetWorthMonth(
                month=start.isoformat(),
                assets=milliunit_to_amount(assets),
                debts=milliunit_to_amount(debts),
                net_worth=milliunit_to_amount(net[-1]),
            )
        )
    return NetWorthTrend(
        months=months,
        first_net_worth=milliunit_to_amount(net[0]),
        last_net_worth=milliunit_to_amount(net[-1]),
        change=milliunit_to_amount(net[-1] - net[0]),
        accounts=[a["name"] for a in accounts if not a["closed"] or any(held[a["id"]])],
    )
