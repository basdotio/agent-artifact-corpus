# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Prepare the classification of pending transactions in one pass.

One download of the plan's transactions serves both as history and as the
list of what is pending: no request per transaction.
"""

from __future__ import annotations

import base64
import string
from datetime import date
from typing import Any

from avenir_mcp import classifier
from avenir_mcp.client import milliunit_to_amount
from avenir_mcp.model import Model
from avenir_mcp.text import untrusted

DEFAULT_LIMIT = 50


class Suggestion(Model):
    """A category proposed from the payee's history."""

    category_id: str
    """Suggested category id."""
    category_name: str
    """Suggested category name."""
    confidence: float
    """Share of the payee's past transactions (same direction) in that category, 0 to 1."""


class Line(Model):
    """A transaction as an agent reads it."""

    transaction_id: str
    """YNAB id of the transaction."""
    date: str
    """Date, YYYY-MM-DD."""
    amount: float
    """Amount in currency units, negative for spending."""
    payee: str
    """Payee as imported, cut to 80 characters. Untrusted bank text."""
    memo: str | None
    """Memo cut to 80 characters, or null. Untrusted bank text."""
    account: str
    """Account name."""


def line_fields(tx: dict[str, Any]) -> dict[str, Any]:
    """Give the fields of a Line for a YNAB transaction, bank text made safe to show.

    Args:
        tx: A YNAB transaction.

    Returns:
        transaction_id, date, amount in currency units, payee, memo and account.
    """
    return {
        "transaction_id": tx["id"],
        "date": tx["date"],
        "amount": milliunit_to_amount(tx["amount"]),
        "payee": untrusted(tx.get("payee_name")),
        "memo": untrusted(tx["memo"]) if tx.get("memo") else None,
        "account": tx.get("account_name") or "",
    }


class PendingItem(Line):
    """A transaction waiting for a category."""

    suggestion: Suggestion | None
    """Category suggested by the history, or null when there is none clear enough."""
    possible_transfer_with: str | None
    """Another pending transaction with the opposite amount on another account, within
    3 days: probably one transfer imported as two. Link them in YNAB rather than
    categorising them. Null otherwise."""


class CategoryChoice(Model):
    """A category the agent may assign."""

    category_id: str
    """Category id to pass to apply_categories."""
    name: str
    """Category name."""
    group: str
    """Name of its group."""


class Triage(Model):
    """One page of pending transactions, with what is needed to classify them."""

    pending_count: int
    """Transactions waiting for a category, in total."""
    suggested_count: int
    """How many of them have a suggestion."""
    items: list[PendingItem]
    """This page of pending transactions, newest first."""
    categories: list[CategoryChoice]
    """Every category that can be assigned; on the first page only, empty on the next ones."""
    next_cursor: str | None
    """Pass it back to get the next page; null on the last page."""


def _encode_cursor(offset: int) -> str:
    """Encode the offset of the next page as an opaque cursor.

    Args:
        offset: Index of the first item of the next page.

    Returns:
        The cursor.
    """
    return base64.urlsafe_b64encode(f"offset:{offset}".encode()).decode()


# The characters of URL-safe Base64, padding included: anything else is not a cursor of ours.
_CURSOR_ALPHABET = frozenset(string.ascii_letters + string.digits + "-_=")


def _decode_cursor(cursor: str) -> int:
    """Decode a cursor made by :func:`_encode_cursor`.

    Args:
        cursor: The next_cursor of a previous page.

    Returns:
        The offset it stands for.

    Raises:
        ValueError: If the cursor was not made by this module, saying what to pass.
    """
    try:
        # Checked first: Python 3.15 warns that it will discard other characters, so an
        # altered cursor could otherwise decode to another page.
        # Asking for a strict subset instead would only refuse a cursor holding every
        # character of the alphabet, which is far too long to decode to an offset and
        # ends in this same refusal anyway.
        if not set(cursor) <= _CURSOR_ALPHABET:  # pragma: no mutate
            raise ValueError(cursor)  # pragma: no mutate
        # Splitting on the last colon instead of the first would only change what a
        # cursor holding several of them decodes to, and neither reading of one leaves
        # the prefix "offset" with digits after it.
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        prefix, _, value = decoded.partition(":")  # pragma: no mutate
        if prefix != "offset" or not value.isdigit():
            # The value given here is never read: the message below is what is raised.
            raise ValueError(cursor)  # pragma: no mutate
    except ValueError as error:  # binascii.Error and UnicodeDecodeError are ValueErrors
        raise ValueError(
            "Invalid cursor: pass the next_cursor value from the previous page unchanged, "
            "or omit it to start from the first page."
        ) from error
    return int(value)


# YNAB's own group, which holds "Inflow: Ready to Assign" and "Uncategorized".
INTERNAL_GROUP = "Internal Master Category"
# Days between the two halves of a transfer imported as two transactions.
TRANSFER_WINDOW_DAYS = 3


CARD_GROUP = "Credit Card Payments"
"""The internal group of the categories that pay credit cards."""
CARD_CATEGORY = (
    "pays a credit card: YNAB ignores it on a transaction. Choose the category of what "
    "was paid for."
)
"""Why a credit card payment category is refused on a transaction or a split line."""


def card_payments(categories: list[dict[str, Any]]) -> set[str]:
    """Find the categories that pay credit cards: YNAB ignores them on a transaction.

    Args:
        categories: The plan's categories.

    Returns:
        Their ids; empty when the plan has no credit card.
    """
    return {c["id"] for c in categories if c.get("category_group_name") == CARD_GROUP}


def internal_uncategorized(categories: list[dict[str, Any]]) -> set[str]:
    """Find YNAB's internal "Uncategorized" category: no choice, and no category.

    Args:
        categories: The plan's categories.

    Returns:
        Its ids; empty when the plan has none.
    """
    return {
        c["id"]
        for c in categories
        if c.get("category_group_name") == INTERNAL_GROUP and c.get("name") == "Uncategorized"
    }


def _is_pending(tx: dict[str, Any], off_budget: set[str], uncategorized: set[str]) -> bool:
    """Tell whether a transaction waits for a category.

    Args:
        tx: A YNAB transaction.
        off_budget: Ids of the tracking accounts.
        uncategorized: Ids of YNAB's internal Uncategorized category.

    Returns:
        True when it is not deleted, not a transfer, not a split (its lines carry the
        categories), on an account that takes categories, and without a real category.
    """
    return (
        not tx.get("deleted")
        and (not tx.get("category_id") or tx["category_id"] in uncategorized)
        and not tx.get("transfer_account_id")
        and not tx.get("subtransactions")
        and tx.get("account_id") not in off_budget
    )


def _transfer_pairs(pending: list[dict[str, Any]]) -> dict[str, str]:
    """Pair pending transactions that look like both halves of one transfer.

    Each outflow takes the first inflow of the opposite amount, on another account,
    within TRANSFER_WINDOW_DAYS. Inflows are looked up by amount, so a plan with
    thousands of pending transactions is paired in one pass rather than one per pair.

    Args:
        pending: The pending transactions.

    Returns:
        Each paired transaction's id mapped to its other half's.
    """
    inflows: dict[int, list[tuple[dict[str, Any], date]]] = {}
    for tx in pending:
        # The only amount these two bounds tell apart is zero, which is money neither in
        # nor out: it is indexed or not, looked for or not, and pairs with nothing either
        # way, since the opposite of zero is zero and no outflow of zero is looked up.
        if tx["amount"] > 0:  # pragma: no mutate
            inflows.setdefault(tx["amount"], []).append((tx, date.fromisoformat(tx["date"])))
    pairs: dict[str, str] = {}
    for tx in pending:
        # Same zero, and only an outflow reaches the lines below, so an id already paired
        # is one of those outflows, which the loop has gone past: no answer can change.
        if tx["id"] in pairs or tx["amount"] >= 0:  # pragma: no mutate
            continue
        day = date.fromisoformat(tx["date"])
        for other, other_day in inflows.get(-tx["amount"], ()):
            if (
                other["id"] not in pairs
                and other.get("account_id") != tx.get("account_id")
                and abs((other_day - day).days) <= TRANSFER_WINDOW_DAYS
            ):
                pairs[tx["id"]], pairs[other["id"]] = other["id"], tx["id"]
                break
    return pairs


def _histories(transactions: list[dict[str, Any]]) -> dict[bool, dict[str, dict[str, int]]]:
    """Learn each payee's categories, money in and money out apart.

    A lender that once paid you does not make your repayments income.

    Args:
        transactions: The plan's transactions.

    Returns:
        Payee histories keyed by direction: True for money out, False for money in.
    """
    known = [
        tx for tx in transactions if not tx.get("deleted") and not tx.get("transfer_account_id")
    ]
    return {
        outflow: classifier.build_payee_history(
            [tx for tx in known if (tx["amount"] < 0) == outflow]
        )
        for outflow in (True, False)
    }


def _suggestion(
    tx: dict[str, Any],
    histories: dict[bool, dict[str, dict[str, int]]],
    categories: list[dict[str, Any]],
    threshold: float | None,
) -> Suggestion | None:
    """Suggest a category for a pending transaction from its payee's history.

    Args:
        tx: The pending transaction.
        histories: Payee histories from :func:`_histories`.
        categories: The plan's categories.
        threshold: Confidence needed; None for the classifier's default.

    Returns:
        The suggestion, or None when the history is not clear enough.
    """
    history = histories[tx["amount"] < 0]
    # The empty default only marks "no payee", and the history is keyed by the merchant
    # a label normalises to, so another default would look up a merchant of that name.
    label = tx.get("payee_name") or ""  # pragma: no mutate
    score = classifier.score_payee(label, history, categories, threshold)
    # The classifier sets the id and the name together or neither, so asking for both
    # and asking for either is the same question: no answer can change.
    if score.category_id is None or score.category_name is None:  # pragma: no mutate
        return None
    return Suggestion(
        category_id=score.category_id,
        category_name=score.category_name,
        confidence=round(score.confidence, 2),
    )


def prepare(  # pylint: disable=too-many-arguments
    transactions: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    *,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
    threshold: float | None = None,
    off_budget: set[str] | frozenset[str] = frozenset(),
) -> Triage:
    """Page through the pending transactions, newest first, with suggestions.

    Args:
        transactions: All the plan's transactions (history and pending).
        categories: The plan's categories.
        limit: Maximum number of items in the page.
        cursor: ``next_cursor`` of the previous page, or None for the first page.
        threshold: Confidence needed for a suggestion; defaults to the classifier's.
        off_budget: Ids of tracking accounts, whose transactions take no category.

    Returns:
        One page, the total pending, the cursor of the next page and, on the first page,
        the categories to choose from.

    Raises:
        ValueError: If ``cursor`` was not issued by this function.
    """
    offset = _decode_cursor(cursor) if cursor else 0
    uncategorized = internal_uncategorized(categories)
    histories = _histories(transactions)
    pending = sorted(
        (tx for tx in transactions if _is_pending(tx, set(off_budget), uncategorized)),
        key=lambda tx: tx["date"],
        reverse=True,
    )
    transfers = _transfer_pairs(pending)
    items = [
        PendingItem(
            **line_fields(tx),
            suggestion=_suggestion(tx, histories, categories, threshold),
            possible_transfer_with=transfers.get(tx["id"]),
        )
        for tx in pending
    ]
    suggested = sum(1 for item in items if item.suggestion is not None)

    end = offset + limit
    return Triage(
        pending_count=len(pending),
        suggested_count=suggested,
        items=items[offset:end],
        categories=(
            []
            if cursor
            else [
                CategoryChoice(
                    category_id=c["id"], name=c["name"], group=c.get("category_group_name", "")
                )
                for c in categories
                if not c.get("deleted") and c["id"] not in uncategorized
            ]
        ),
        next_cursor=_encode_cursor(end) if end < len(items) else None,
    )
