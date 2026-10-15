# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""A plan's payees: the labels banks give them, and the rename of one.

A card payment carries the date and the card number in its label, so one shop can
end up as many payees. Listing them with the merchant each label normalises to
shows which ones name the same shop; renaming one to the merchant's name fixes it
at the source, for every transaction that names it.
"""

from __future__ import annotations

from typing import Any

from avenir_mcp.classifier import normalize_payee
from avenir_mcp.model import Model
from avenir_mcp.text import one_line, untrusted

DEFAULT_LISTED = 50
"""Payees listed when the agent asks for no limit."""
MAX_LISTED = 200
"""Most payees one answer carries: more would fill an agent's context."""
MAX_NAME = 500
"""YNAB refuses a payee name longer than this (SavePayee.name)."""


class Payee(Model):
    """One payee of the plan, and how the plan uses it."""

    payee_id: str
    """YNAB id of the payee, to pass to rename_payee."""
    name: str
    """Its name, as the bank wrote it (untrusted text, on one line)."""
    merchant: str
    """The merchant its label normalises to: two labels sharing one name the same shop."""
    transactions: int
    """How many transactions name it."""
    last_date: str | None
    """Date (YYYY-MM-DD) of the latest transaction naming it; null for none."""


class PayeeList(Model):
    """The payees of a plan, those used most first."""

    payees: list[Payee]
    """The payees, most transactions first, then by name."""
    total: int
    """How many payees match, before the limit."""
    shown: int
    """How many are listed here."""


class RenamePlan(Model):
    """What renaming one payee would change.

    The names are as YNAB holds them: a tool makes them safe before showing them.
    """

    payee_id: str
    """The payee to rename."""
    from_name: str
    """Its name now."""
    to_name: str
    """The name to send YNAB, trimmed."""
    transactions: int
    """How many transactions name it, and would show the new name."""


def _usage(transactions: list[dict[str, Any]]) -> dict[str, tuple[int, str]]:
    """Count the transactions of each payee, and keep the latest date.

    Args:
        transactions: The plan's transactions, as YNAB returns them.

    Returns:
        Payee id -> (how many transactions name it, the latest one's date).
    """
    usage: dict[str, tuple[int, str]] = {}
    for tx in transactions:
        payee_id = tx.get("payee_id")
        if not payee_id or tx.get("deleted"):
            continue
        count, latest = usage.get(payee_id, (0, ""))
        usage[payee_id] = (count + 1, max(latest, tx["date"]))
    return usage


def usable(payees: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the payees a user may rename.

    A deleted payee is gone, and YNAB names a transfer's payee after the account it
    moves money to: renaming it would not stick.

    Args:
        payees: The plan's payees, as YNAB returns them.

    Returns:
        The payees left, in YNAB's order.
    """
    return [
        payee
        for payee in payees
        if not payee.get("deleted") and not payee.get("transfer_account_id")
    ]


def listing(
    payees: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    search: str | None = None,
    limit: int = DEFAULT_LISTED,
) -> PayeeList:
    """List the payees of a plan, those used most first.

    Args:
        payees: The plan's payees, as YNAB returns them.
        transactions: The plan's transactions, to count each payee's use.
        search: Keep only the payees whose label or merchant holds this text,
            whatever the case; None for all of them.
        limit: Most payees to list.

    Returns:
        The payees, how many match and how many are listed.
    """
    usage = _usage(transactions)
    found = []
    for payee in usable(payees):
        count, latest = usage.get(payee["id"], (0, ""))
        found.append(
            Payee(
                payee_id=payee["id"],
                name=untrusted(payee["name"]),
                merchant=normalize_payee(payee["name"]),
                transactions=count,
                last_date=latest or None,
            )
        )
    if search is not None:
        needle = search.casefold()
        found = [p for p in found if needle in p.name.casefold() or needle in p.merchant.casefold()]
    found.sort(key=lambda p: (-p.transactions, p.name.casefold()))
    return PayeeList(payees=found[:limit], total=len(found), shown=len(found[:limit]))


def plan_rename(
    payees: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    payee_id: str,
    name: str,
) -> RenamePlan:
    """Say what renaming a payee would change.

    Args:
        payees: The plan's payees, as YNAB returns them.
        transactions: The plan's transactions, to count what the rename affects.
        payee_id: The payee to rename.
        name: The name to give it.

    Returns:
        The payee, its name before and after, and how many transactions name it;
        the two names are equal when there is nothing to change.

    Raises:
        ValueError: If the payee is not one of the plan's, is a transfer's, or the new
            name is empty, longer than YNAB accepts, not on one line of visible
            characters, or already another payee's.
    """
    transfers = {p["id"] for p in payees if p.get("transfer_account_id")}
    if payee_id in transfers:
        raise ValueError(
            f"Payee {payee_id} is a transfer's: YNAB names it after the account the money "
            "moves to. Rename the account in YNAB itself."
        )
    payee = next((p for p in usable(payees) if p["id"] == payee_id), None)
    if payee is None:
        raise ValueError(f"Payee {payee_id} is not in this plan: use a payee_id from list_payees.")
    new_name = name.strip()
    if not new_name:
        raise ValueError("The new name is empty: give the merchant's name.")
    if len(new_name) > MAX_NAME:
        raise ValueError(
            f"The new name is {len(new_name)} characters: YNAB refuses a payee name longer "
            f"than {MAX_NAME}."
        )
    one_line(new_name)
    taken = {p["name"].casefold() for p in payees if not p.get("deleted") and p["id"] != payee_id}
    if new_name.casefold() in taken:
        raise ValueError(
            f"{untrusted(new_name)!r} is already the name of another payee: YNAB's API cannot "
            "merge two payees. Merge them in YNAB, or choose another name."
        )
    # Only the count is wanted here, so the latest date of the default pair was never
    # read: asking for the count alone leaves no value behind that no test can reach.
    used = _usage(transactions)
    return RenamePlan(
        payee_id=payee_id,
        from_name=payee["name"],
        to_name=new_name,
        transactions=used[payee_id][0] if payee_id in used else 0,
    )
