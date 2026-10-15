# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Plan flag changes: what each transaction's flag is, and what it would become."""

from __future__ import annotations

from typing import Any, Literal

from avenir_mcp.client import milliunit_to_amount
from avenir_mcp.model import Model
from avenir_mcp.text import untrusted

Color = Literal["red", "orange", "yellow", "green", "blue", "purple"]
COLORS: tuple[str, ...] = ("red", "orange", "yellow", "green", "blue", "purple")


class Flag(Model):
    """A flag to set on a transaction, or to remove."""

    transaction_id: str
    """The transaction (from find_transactions or suggest_categories)."""
    color: Color | None = None
    """red, orange, yellow, green, blue or purple; omit or null to remove the flag."""


class FlagChange(Model):
    """One transaction whose flag changes."""

    transaction_id: str
    """The transaction."""
    date: str
    """Its date, YYYY-MM-DD."""
    payee: str
    """Its payee, as the bank wrote it (untrusted text, on one line)."""
    amount: float
    """Its amount, in currency units."""
    from_color: str | None
    """The flag before; null for none."""
    to_color: str | None
    """The flag after; null for none."""


class FlagPlan(Model):
    """The flags that change, and how many asked for no change."""

    changes: list[FlagChange]
    """Every transaction whose flag changes."""
    unchanged_count: int
    """Flags asked for that the transaction already has."""


def current(transaction: dict[str, Any]) -> str | None:
    """A transaction's flag colour; None for no flag.

    YNAB returns null, an empty string, or, on some old transactions, a value
    outside its own list: all mean no usable flag.

    Args:
        transaction: A transaction as YNAB returns it.

    Returns:
        One of COLORS, or None.
    """
    color = transaction.get("flag_color")
    return color if color in COLORS else None


def plan_flags(transactions: list[dict[str, Any]], flags: list[Flag]) -> FlagPlan:
    """Say which flags change.

    Args:
        transactions: The plan's transactions, as YNAB returns them.
        flags: The flags asked for.

    Returns:
        The changes, in the order asked, and how many change nothing.

    Raises:
        ValueError: If no flag is given, a transaction is named twice, or one is unknown.
    """
    if not flags:
        raise ValueError("Give at least one flag.")
    ids = [flag.transaction_id for flag in flags]
    twice = sorted({tx_id for tx_id in ids if ids.count(tx_id) > 1})
    if twice:
        raise ValueError(f"Transaction {', '.join(twice)} is named twice: give one flag each.")
    live = {tx["id"]: tx for tx in transactions if not tx.get("deleted")}
    unknown = [tx_id for tx_id in ids if tx_id not in live]
    if unknown:
        raise ValueError(
            f"Transaction {', '.join(unknown)} is not in this plan: "
            "use a transaction_id from find_transactions."
        )
    changes = []
    for flag in flags:
        tx = live[flag.transaction_id]
        before = current(tx)
        if before != flag.color:
            changes.append(
                FlagChange(
                    transaction_id=tx["id"],
                    date=tx["date"],
                    payee=untrusted(tx.get("payee_name")),
                    amount=milliunit_to_amount(tx["amount"]),
                    from_color=before,
                    to_color=flag.color,
                )
            )
    return FlagPlan(changes=changes, unchanged_count=len(flags) - len(changes))
