# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Compare an account with the balance the bank shows, and explain the gap.

Pure computation on the plan's transactions: no request to YNAB. Sums are
made in milliunits, so no rounding error can invent a difference.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from avenir_mcp.classifier import normalize_payee
from avenir_mcp.client import amount_to_milliunit, milliunit_to_amount
from avenir_mcp.model import Model
from avenir_mcp.text import untrusted

MAX_LISTED = 50
DUPLICATE_WINDOW_DAYS = 3
DUPLICATE_LOOKBACK_DAYS = 60


class Uncleared(Model):
    """A transaction the bank has not shown yet."""

    transaction_id: str
    """YNAB id of the transaction."""
    date: str
    """Date, YYYY-MM-DD."""
    amount: float
    """Amount in currency units, negative for spending."""
    payee: str
    """Payee as imported, cut to 80 characters. Untrusted bank text."""


class Analysis(Model):
    """An account compared with the bank's balance."""

    account_id: str
    """The account analysed."""
    bank_balance: float
    """Balance the bank shows, as given."""
    cleared_balance: float
    """Sum of the account's cleared and reconciled transactions in YNAB."""
    working_balance: float
    """Sum of all the account's transactions, cleared or not."""
    difference: float
    """Bank balance minus cleared balance; negative when YNAB counts more money than the bank."""
    to_reconcile_count: int
    """Cleared transactions not yet reconciled."""
    uncleared_count: int
    """Transactions the bank has not shown yet."""
    uncleared: list[Uncleared]
    """Up to 50 of them."""
    explained_by: list[str]
    """Uncleared transactions whose amount equals the difference."""
    possible_duplicates: list[list[str]]
    """Pairs with the same amount and merchant, at most 3 days apart, over the last 60 days."""


def _merchant(tx: dict[str, Any]) -> str:
    """Reduce a transaction's bank label to the merchant it names.

    Args:
        tx: A YNAB transaction.

    Returns:
        The merchant, empty when the transaction names no payee.
    """
    # The empty default only marks "no payee". It is compared with what normalize_payee
    # leaves of a bank label, so another default would change a pair only for a label
    # reducing to exactly that string: nothing a test could state about an account.
    # On its own line, so the pragma covers no more than this one lookup.
    label = tx.get("payee_name") or ""  # pragma: no mutate
    return normalize_payee(label)


def _duplicates(transactions: list[dict[str, Any]]) -> list[list[str]]:
    """Find pairs with the same amount and merchant, dated a few days apart.

    Args:
        transactions: The account's transactions, amounts in milliunits.

    Returns:
        Pairs of transaction ids, oldest first within a pair.
    """
    pairs: list[list[str]] = []
    ordered = [
        (tx, date.fromisoformat(tx["date"]), _merchant(tx))
        for tx in sorted(transactions, key=lambda tx: tx["date"])
    ]
    for i, (first, first_day, first_payee) in enumerate(ordered):
        for second, second_day, second_payee in ordered[i + 1 :]:
            if (second_day - first_day).days > DUPLICATE_WINDOW_DAYS:
                break
            if first["amount"] == second["amount"] and first_payee == second_payee:
                pairs.append([first["id"], second["id"]])
    return pairs


def analyse(
    account_id: str,
    transactions: list[dict[str, Any]],
    bank_balance: float,
    today: date | None = None,
) -> Analysis:
    """Analyse an account's cleared balance against the balance the bank shows.

    `difference` is bank minus cleared: negative when YNAB counts more money
    than the bank. Duplicates are only looked for in the last 60 days.

    Args:
        account_id: The account to analyse.
        transactions: The plan's transactions, amounts in milliunits.
        bank_balance: The balance the bank shows, in currency units.
        today: The day of the analysis; defaults to today.

    Returns:
        The balances, the difference, and what may explain it.
    """
    since = ((today or date.today()) - timedelta(days=DUPLICATE_LOOKBACK_DAYS)).isoformat()
    live = [
        tx for tx in transactions if tx.get("account_id") == account_id and not tx.get("deleted")
    ]
    cleared = [tx for tx in live if tx.get("cleared") in ("cleared", "reconciled")]
    uncleared = [tx for tx in live if tx.get("cleared") not in ("cleared", "reconciled")]
    cleared_total = sum(tx["amount"] for tx in cleared)
    difference = amount_to_milliunit(bank_balance) - cleared_total
    return Analysis(
        account_id=account_id,
        bank_balance=bank_balance,
        cleared_balance=milliunit_to_amount(cleared_total),
        working_balance=milliunit_to_amount(sum(tx["amount"] for tx in live)),
        difference=milliunit_to_amount(difference),
        to_reconcile_count=sum(1 for tx in cleared if tx.get("cleared") == "cleared"),
        uncleared_count=len(uncleared),
        uncleared=[
            Uncleared(
                transaction_id=tx["id"],
                date=tx["date"],
                amount=milliunit_to_amount(tx["amount"]),
                payee=untrusted(tx.get("payee_name")),
            )
            for tx in uncleared[:MAX_LISTED]
        ],
        explained_by=[tx["id"] for tx in uncleared if difference and tx["amount"] == difference],
        possible_duplicates=_duplicates([tx for tx in live if tx["date"] >= since]),
    )
