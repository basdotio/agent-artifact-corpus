# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Plan how one transaction is split across categories, e.g. from a receipt.

Nothing here talks to YNAB. The plan checks what YNAB would refuse, and what
cannot be what the user meant: lines that do not add up to the transaction to
the cent.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from avenir_mcp.amounts import Amount
from avenir_mcp.client import amount_to_milliunit, milliunit_to_amount
from avenir_mcp.model import Model
from avenir_mcp.text import MAX_MEMO, YnabText, untrusted
from avenir_mcp.triage import CARD_CATEGORY, card_payments, internal_uncategorized


class SplitLine(Model):
    """One line of a split: an amount and its category."""

    amount: Amount
    """Amount in currency units, negative for spending; the lines add up to the transaction."""
    category_id: str
    """Category of this line."""
    memo: YnabText | None = Field(default=None, max_length=MAX_MEMO)
    """Optional note for this line, e.g. what the receipt lists; at most 500 characters."""


class SplitLinePreview(Model):
    """A line of a split, as the user sees it."""

    amount: float
    """Amount in currency units."""
    category: str
    """Category name."""
    memo: str | None
    """Note; null if none."""


class SplitPlan(Model):
    """The transaction to split and the lines it would get."""

    transaction_id: str
    """YNAB id of the transaction."""
    date: str
    """Date, YYYY-MM-DD."""
    payee: str
    """Payee as imported. Untrusted bank text."""
    amount: float
    """Amount of the transaction, in currency units."""
    from_category: str | None
    """Category the split replaces; null for none."""
    lines: list[SplitLinePreview]
    """The lines, in the order given."""


def _is_split(tx: dict[str, Any]) -> bool:
    """Tell whether a transaction already has live split lines.

    Args:
        tx: A YNAB transaction.

    Returns:
        True when one of its subtransactions is not deleted.
    """
    return any(not sub.get("deleted") for sub in tx.get("subtransactions") or [])


def _is_unsplittable_transfer(tx: dict[str, Any], off_budget: set[str] | frozenset[str]) -> bool:
    """Tell whether YNAB refuses to split this transfer.

    Args:
        tx: A YNAB transaction.
        off_budget: Ids of the tracking accounts.

    Returns:
        False when it is no transfer, and for the one transfer YNAB splits: from an
        on-budget account to a tracking one. True for any other transfer.
    """
    other = tx.get("transfer_account_id")
    if not other:
        return False
    return other not in off_budget or tx.get("account_id") in off_budget


def _check_transaction(tx: dict[str, Any], off_budget: set[str] | frozenset[str]) -> None:
    """Refuse a transaction YNAB cannot split.

    Args:
        tx: The transaction.
        off_budget: Ids of the tracking accounts.

    Raises:
        ValueError: If it was deleted, is already split, a transfer other than one from an
            on-budget account to a tracking one, or on an off-budget account.
    """
    tx_id = tx["id"]
    if tx.get("deleted"):
        raise ValueError(f"Transaction {tx_id} was deleted in YNAB: there is nothing to split.")
    if _is_split(tx):
        raise ValueError(
            f"Transaction {tx_id} is already split: YNAB's API cannot change its lines, "
            "change them in YNAB."
        )
    if _is_unsplittable_transfer(tx, off_budget):
        raise ValueError(f"Transaction {tx_id} is a transfer between accounts: it cannot be split.")
    if tx.get("account_id") in off_budget:
        raise ValueError(
            f"Transaction {tx_id} is on an off-budget account: YNAB does not split those."
        )


def _check_lines(
    tx: dict[str, Any],
    names: dict[str, str],
    refused: tuple[set[str], set[str]],
    lines: list[SplitLine],
) -> None:
    """Refuse lines that name no real category or do not add up to the transaction.

    Args:
        tx: The transaction.
        names: The plan's category names by id.
        refused: Ids of YNAB's internal Uncategorized, and of the categories that pay
            credit cards.
        lines: The lines proposed.

    Raises:
        ValueError: If there are fewer than two lines, a line is zero, a category is
            unknown, internal or pays a credit card, or the sum differs from the
            transaction.
    """
    uncategorized, cards = refused
    if len(lines) < 2:
        raise ValueError(
            "Give at least two lines: to give the whole transaction one category, "
            "use apply_categories."
        )
    total = 0
    for line in lines:
        milliunits = amount_to_milliunit(line.amount)
        if milliunits == 0:
            raise ValueError("A line is zero: leave it out.")
        if line.category_id in uncategorized:
            raise ValueError(
                f"Category {line.category_id} is YNAB's internal Uncategorized: "
                "choose a real category."
            )
        if line.category_id not in names:
            raise ValueError(
                f"Category {line.category_id} is not in this plan: "
                "use a category_id from suggest_categories or get_category_balances."
            )
        if line.category_id in cards:
            raise ValueError(f"Category {line.category_id} {CARD_CATEGORY}")
        total += milliunits
    if total != tx["amount"]:
        raise ValueError(
            f"The lines add up to {milliunit_to_amount(total):.2f}, the transaction is "
            f"{milliunit_to_amount(tx['amount']):.2f}: they must match to the cent."
        )


def plan_split(
    transactions: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    transaction_id: str,
    lines: list[SplitLine],
    off_budget: set[str] | frozenset[str] = frozenset(),
) -> SplitPlan:
    """Work out the split of one transaction, refusing what cannot be meant.

    Args:
        transactions: The plan's transactions.
        categories: The plan's categories.
        transaction_id: The transaction to split.
        lines: Its lines, at least two, adding up to its amount.
        off_budget: Ids of the tracking accounts.

    Returns:
        The transaction and its lines, as the user will see them.

    Raises:
        ValueError: With a message saying what to fix, if the transaction is unknown,
            deleted, already split, off-budget, or a transfer other than one from an on-budget
            account to a tracking one, or if the lines are fewer than two, zero, in an unknown
            or internal category, or do not add up.
    """
    tx = next((t for t in transactions if t["id"] == transaction_id), None)
    if tx is None:
        raise ValueError(
            f"Transaction {transaction_id} is not in this plan: "
            "use a transaction_id returned by suggest_categories."
        )
    _check_transaction(tx, off_budget)
    names = {c["id"]: c["name"] for c in categories}
    refused = (internal_uncategorized(categories), card_payments(categories))
    _check_lines(tx, names, refused, lines)
    current = tx.get("category_id")
    return SplitPlan(
        transaction_id=transaction_id,
        date=tx["date"],
        payee=untrusted(tx.get("payee_name")),
        amount=milliunit_to_amount(tx["amount"]),
        from_category=untrusted(names.get(current)) or None,
        lines=[
            SplitLinePreview(
                amount=line.amount,
                category=untrusted(names[line.category_id]),
                memo=untrusted(line.memo) if line.memo else None,
            )
            for line in lines
        ],
    )
