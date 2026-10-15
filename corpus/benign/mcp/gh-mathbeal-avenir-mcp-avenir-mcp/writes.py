# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Plan a change to a plan and confirm it before it happens.

Nothing here talks to YNAB. A plan says exactly what would change; a
confirmation code, issued for one plan, lets a client without elicitation
confirm that plan and no other.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from collections.abc import Callable
from typing import Any

from pydantic import TypeAdapter

from avenir_mcp.client import milliunit_to_amount
from avenir_mcp.journal import Move
from avenir_mcp.model import Model
from avenir_mcp.text import untrusted
from avenir_mcp.triage import CARD_CATEGORY, card_payments, internal_uncategorized

CONFIRMATION_TTL_SECONDS = 600
# Turns what is confirmed, models included, into plain JSON data before hashing it.
_JSON: TypeAdapter[Any] = TypeAdapter(Any)


class Assignment(Model):
    """A category to give to a transaction."""

    transaction_id: str
    """Transaction to categorise, from suggest_categories."""
    category_id: str
    """Category to give it."""


class Change(Model):
    """One transaction moving from a category to another."""

    transaction_id: str
    """YNAB id of the transaction."""
    date: str
    """Date, YYYY-MM-DD."""
    amount: float
    """Amount in currency units."""
    payee: str
    """Payee as imported. Untrusted bank text."""
    from_category_id: str | None
    """Category id before; null for none."""
    from_category: str | None
    """Category name before; null for none."""
    to_category_id: str | None
    """Category id after; null for none."""
    to_category: str | None
    """Category name after; null for none."""


class Plan(Model):
    """What an operation would change, and what it leaves alone."""

    changes: list[Change] = []
    """Transactions that would change."""
    unchanged_count: int = 0
    """Assignments that change nothing."""
    conflicts: list[str] = []
    """Ids left alone because they changed since."""


def _check_category(
    category_id: str, names: dict[str, str], refused: tuple[set[str], set[str]]
) -> None:
    """Refuse a category YNAB would not put on a transaction.

    Args:
        category_id: The category asked for.
        names: The plan's category names by id.
        refused: Ids of YNAB's internal Uncategorized, and of the categories that pay
            credit cards.

    Raises:
        ValueError: If the category is internal, unknown, or pays a credit card.
    """
    uncategorized, cards = refused
    if category_id in uncategorized:
        raise ValueError(
            f"Category {category_id} is YNAB's internal Uncategorized: choose a real category."
        )
    if category_id not in names:
        raise ValueError(
            f"Category {category_id} is not in this plan: "
            "use a category_id from the categories returned by suggest_categories."
        )
    if category_id in cards:
        raise ValueError(f"Category {category_id} {CARD_CATEGORY}")


def plan_categorization(
    transactions: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    assignments: list[Assignment],
    off_budget: set[str] | frozenset[str] = frozenset(),
) -> Plan:
    """Work out what assigning these categories would change.

    Args:
        transactions: The plan's transactions.
        categories: The plan's categories.
        assignments: The categories to give, one per transaction.
        off_budget: Ids of the tracking accounts.

    Returns:
        The changes, and how many assignments change nothing.

    Raises:
        ValueError: With a message saying what to fix, if an assignment names an
            unknown transaction or category, a transfer, a split, a transaction of
            an off-budget account, YNAB's internal Uncategorized, a credit card
            payment category, or a transaction twice.
    """
    by_id = {tx["id"]: tx for tx in transactions}
    names = {c["id"]: c["name"] for c in categories}
    refused = (internal_uncategorized(categories), card_payments(categories))
    seen: set[str] = set()
    changes: list[Change] = []
    unchanged = 0
    for assignment in assignments:
        tx_id, category_id = assignment.transaction_id, assignment.category_id
        if tx_id in seen:
            raise ValueError(f"Transaction {tx_id} is assigned twice: keep one assignment.")
        seen.add(tx_id)
        tx = by_id.get(tx_id)
        if tx is None:
            raise ValueError(
                f"Transaction {tx_id} is not in this plan: "
                "use the transaction_id values returned by suggest_categories."
            )
        _check_category(category_id, names, refused)
        if tx.get("subtransactions"):
            raise ValueError(
                f"Transaction {tx_id} is split across categories: change its lines in YNAB."
            )
        if tx.get("account_id") in off_budget:
            raise ValueError(
                f"Transaction {tx_id} is on an off-budget account: YNAB gives it no category."
            )
        if tx.get("transfer_account_id"):
            raise ValueError(
                f"Transaction {tx_id} is a transfer between accounts: YNAB gives it no category."
            )
        current = tx.get("category_id")
        if current == category_id:
            unchanged += 1
            continue
        changes.append(
            Change(
                transaction_id=tx_id,
                date=tx["date"],
                amount=milliunit_to_amount(tx["amount"]),
                payee=untrusted(tx.get("payee_name")),
                from_category_id=current,
                from_category=untrusted(names.get(current)) or None,
                to_category_id=category_id,
                to_category=untrusted(names[category_id]),
            )
        )
    return Plan(changes=changes, unchanged_count=unchanged)


def plan_undo(
    transactions: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    moves: list[Move],
) -> Plan:
    """Work out what undoing these moves would change.

    A transaction whose category changed again since the operation is left
    alone and listed in ``conflicts``, so that undo never overwrites later work.

    Args:
        transactions: The plan's transactions.
        categories: The plan's categories.
        moves: The operation's moves, from the journal.

    Returns:
        The changes back, and the transactions left alone.
    """
    by_id = {tx["id"]: tx for tx in transactions}
    names = {c["id"]: c["name"] for c in categories}
    changes: list[Change] = []
    conflicts: list[str] = []
    for move in moves:
        tx = by_id.get(move.transaction_id)
        if tx is None or tx.get("category_id") != move.to_category_id:
            conflicts.append(move.transaction_id)
            continue
        before = move.from_category_id
        # The empty default only marks "no category". It is looked up among the plan's
        # ids, which YNAB writes as UUIDs, so another default would be found only if a
        # category carried that very id.
        gave = move.to_category_id or ""  # pragma: no mutate
        changes.append(
            Change(
                transaction_id=tx["id"],
                date=tx["date"],
                amount=milliunit_to_amount(tx["amount"]),
                payee=untrusted(tx.get("payee_name")),
                from_category_id=move.to_category_id,
                from_category=untrusted(names.get(gave)) or None,
                to_category_id=before,
                to_category=untrusted(names.get(before)) if before else None,
            )
        )
    return Plan(changes=changes, conflicts=conflicts)


def fingerprint(plan_id: str, subject: object) -> str:
    """Hash what is being confirmed; the order of a list of changes does not matter.

    Args:
        plan_id: YNAB plan id or 'last-used'.
        subject: The exact change, as JSON data or models.

    Returns:
        A SHA-256 hex digest.
    """
    subject = _JSON.dump_python(subject, mode="json")
    if isinstance(subject, list):
        subject = sorted(json.dumps(item, sort_keys=True) for item in subject)
    # Whatever this call writes is hashed and only ever compared with a digest made the
    # same way: how compact the JSON is, and whether a two-item list is sorted, change
    # the digest without changing which plans match. Sorting what matters happens above.
    data = [plan_id, subject]
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))  # pragma: no mutate
    return hashlib.sha256(payload.encode()).hexdigest()


class Confirmations:
    """Single-use confirmation codes, each bound to one exact plan."""

    def __init__(
        self,
        ttl_seconds: float = CONFIRMATION_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Start with no code issued.

        Args:
            ttl_seconds: How long a code stays valid.
            clock: Seconds from an arbitrary start; replaceable in tests.
        """
        self._ttl = ttl_seconds
        self._clock = clock
        self._issued: dict[str, tuple[str, float]] = {}

    def issue(self, plan_id: str, subject: object) -> str:
        """Issue a code that confirms this subject, and nothing else.

        Expired codes are dropped first, so previews never confirmed do not pile up.

        Args:
            plan_id: YNAB plan id or 'last-used'.
            subject: The exact change previewed, as JSON data or models.

        Returns:
            The new code.
        """
        now = self._clock()
        self._issued = {c: v for c, v in self._issued.items() if now - v[1] <= self._ttl}
        code = secrets.token_urlsafe(8)
        self._issued[code] = (fingerprint(plan_id, subject), now)
        return code

    def consume(self, code: str, plan_id: str, subject: object) -> bool:
        """Spend a code.

        Args:
            code: The code the agent passed back.
            plan_id: YNAB plan id or 'last-used'.
            subject: The exact change the agent wants to make now.

        Returns:
            True only if the code was issued for this subject and is still fresh.
        """
        issued = self._issued.pop(code, None)
        if issued is None:
            return False
        expected, issued_at = issued
        fresh = self._clock() - issued_at <= self._ttl
        return fresh and expected == fingerprint(plan_id, subject)
