# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Undo an operation recorded in the journal, whatever its kind."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp.types import InputRequiredResult

from avenir_mcp import client, flags, journal, targets, writes
from avenir_mcp.app import WRITE_TAG, mcp
from avenir_mcp.confirm import WriteResult, ask, not_applied, result_of, write_plan
from avenir_mcp.text import untrusted

logger = logging.getLogger(__name__)


@mcp.tool(
    tags={WRITE_TAG},
    annotations={
        "title": "Undo an operation",
        "read_only_hint": False,
        "destructive_hint": True,
        "idempotent_hint": False,
        "open_world_hint": True,
    },
)
# One branch per kind of operation, each a direct call: docsgen's API coverage follows
# calls from the tools down to YNAB, and a table of functions would hide them.
# pylint: disable-next=too-many-return-statements
async def undo_operation(
    plan_id: str,
    ctx: Context,
    operation_id: str | None = None,
    confirmation: str | None = None,
) -> WriteResult | InputRequiredResult:
    """Undo an operation made through this server: the latest one, or the one named.

    Recategorised transactions go back to their previous category; a
    reconciliation is reverted (statuses and adjustment); a budgeted amount goes
    back to its previous value, both of a move_money; created transactions are deleted; flags
    go back to their previous colour; a target goes back to what it was; a renamed
    payee gets its old name back. Anything
    changed again since the operation is left alone and listed in `conflicts`.
    Confirmation works as for apply_categories.

    Args:
        plan_id: YNAB plan id or 'last-used'.
        ctx: The MCP context, used to ask the user.
        operation_id: Operation to undo; omit for the most recent one.
        confirmation: Code from a previous "confirmation_required" result.

    Returns:
        What was reverted and what was left alone, or an input request the client answers by asking
        the user (protocol 2026-07-28).

    Raises:
        ToolError: If the journal is damaged, no operation of the plan is still in
            effect (with that id), or the confirmation code is refused.
    """
    logger.info("Tool called: undo_operation")
    book = journal.Journal(journal.default_path())
    try:
        entry = book.find(plan_id, operation_id)
    except ValueError as error:
        raise ToolError(str(error)) from error
    if entry is None:
        raise ToolError(
            "Nothing to undo: no operation of this plan is still in effect"
            + (f" with id {operation_id}." if operation_id else ".")
        )
    if entry.kind == "reconcile":
        return await _undo_reconcile(ctx, plan_id, book, entry, confirmation)
    if entry.kind == "budget":
        return await _undo_budget(ctx, plan_id, book, entry, confirmation)
    if entry.kind == "move":
        return await _undo_move(ctx, plan_id, book, entry, confirmation)
    if entry.kind == "create":
        return await _undo_create(ctx, plan_id, book, entry, confirmation)
    if entry.kind == "flag":
        return await _undo_flag(ctx, plan_id, book, entry, confirmation)
    if entry.kind == "target":
        return await _undo_target(ctx, plan_id, book, entry, confirmation)
    if entry.kind == "payee":
        return await _undo_payee(ctx, plan_id, book, entry, confirmation)
    transactions = await client.get_transactions(plan_id)
    categories = await client.get_categories(plan_id)
    plan = writes.plan_undo(transactions, categories, entry.moves)
    result, new_operation = await write_plan(ctx, plan_id, plan, "Undo: recategorise", confirmation)
    if new_operation is not None:
        book.mark_undone(entry.operation_id)
        book.mark_undone(new_operation)
    return result


async def _confirm_undo(
    ctx: Context, plan_id: str, entry: journal.Entry, question: str, confirmation: str | None
) -> WriteResult | InputRequiredResult | None:
    """Ask the user to confirm an undo.

    Args:
        ctx: The MCP context, used to ask the user.
        plan_id: YNAB plan id or 'last-used'.
        entry: The operation to undo.
        question: What the user is asked.
        confirmation: A code from a previous preview, or None.

    Returns:
        None when the user agreed; otherwise what to return instead of undoing.
    """
    decision = await ask(ctx, plan_id, {"undo": entry.operation_id}, question, confirmation)
    if isinstance(decision, InputRequiredResult):
        return decision
    outcome = not_applied(decision, question)
    if outcome is None:
        return None
    return result_of(
        outcome.status, outcome.message, writes.Plan(), confirmation=outcome.confirmation
    )


def _undone(
    book: journal.Journal, entry: journal.Entry, done: str, conflicts: list[str] | None = None
) -> WriteResult:
    """Record that an operation has been undone, and say what was put back.

    Args:
        book: The journal, to mark the operation undone.
        entry: The operation undone.
        done: What the user is told was put back.
        conflicts: Ids left alone because they changed since; None when there are none.

    Returns:
        The applied result, carrying those conflicts.
    """
    book.mark_undone(entry.operation_id)
    return result_of("applied", done, writes.Plan(conflicts=conflicts or []))


async def _undo_reconcile(
    ctx: Context,
    plan_id: str,
    book: journal.Journal,
    entry: journal.Entry,
    confirmation: str | None,
) -> WriteResult | InputRequiredResult:
    """Put reconciled transactions back to cleared and delete the adjustment, if any.

    Args:
        ctx: The MCP context, used to ask the user.
        plan_id: YNAB plan id or 'last-used'.
        book: The journal, to mark the operation undone.
        entry: The operation to undo.
        confirmation: A code from a previous preview, or None.

    Returns:
        What was done, or what to return instead when the user did not agree.
    """
    details = entry.details
    statuses = {tx["id"]: tx for tx in await client.get_transactions(plan_id)}
    reverted = [
        tx_id
        for tx_id in details["reconciled_ids"]
        if statuses.get(tx_id, {}).get("cleared") == "reconciled"
    ]
    adjustment = details.get("adjustment_id")
    question = f"Undo reconciliation: mark {len(reverted)} transaction(s) back to cleared" + (
        " and delete the balance adjustment?" if adjustment else "?"
    )
    if (refused := await _confirm_undo(ctx, plan_id, entry, question, confirmation)) is not None:
        return refused
    await client.set_transactions_cleared(plan_id, reverted, "cleared")
    if adjustment:
        await client.delete_transaction(plan_id, adjustment)
    return _undone(book, entry, "Reconciliation undone.")


async def _undo_budget(
    ctx: Context,
    plan_id: str,
    book: journal.Journal,
    entry: journal.Entry,
    confirmation: str | None,
) -> WriteResult | InputRequiredResult:
    """Set a category's budgeted amount back to what it was, unless it moved since.

    Args:
        ctx: The MCP context, used to ask the user.
        plan_id: YNAB plan id or 'last-used'.
        book: The journal, to mark the operation undone.
        entry: The operation to undo.
        confirmation: A code from a previous preview, or None.

    Returns:
        What was done, or what to return instead when the user did not agree.
    """
    details = entry.details
    categories = await client.get_month_categories(plan_id, details["month"])
    current = next((c for c in categories if c["id"] == details["category_id"]), None)
    if current is None or current["budgeted"] != details["to"]:
        conflict = writes.Plan(conflicts=[details["category_id"]])
        return result_of("nothing_to_do", "The amount changed since: left alone.", conflict)
    previous = client.milliunit_to_amount(details["from"])
    question = (
        f"Undo: set {untrusted(current['name'])} for {details['month']} back to {previous:.2f}?"
    )
    if (refused := await _confirm_undo(ctx, plan_id, entry, question, confirmation)) is not None:
        return refused
    await client.set_category_budgeted(plan_id, details["month"], details["category_id"], previous)
    return _undone(book, entry, "Budgeted amount restored.")


def _move_back_question(
    current: dict[str, dict[str, Any]], changes: list[dict[str, Any]], month: str
) -> str:
    """Say what undoing a move does, for the user to confirm.

    Args:
        current: The month's categories by id.
        changes: The move's two changes, source first, as the journal holds them.
        month: The month, YYYY-MM-01.

    Returns:
        The question, naming the amount and both categories.
    """
    source, target = (untrusted(current[change["category_id"]]["name"]) for change in changes)
    amount = client.milliunit_to_amount(changes[0]["from"] - changes[0]["to"])
    return f"Undo: move {amount:.2f} back from {target} to {source} for {month}?"


async def _undo_move(
    ctx: Context,
    plan_id: str,
    book: journal.Journal,
    entry: journal.Entry,
    confirmation: str | None,
) -> WriteResult | InputRequiredResult:
    """Put both categories of a move back, unless either changed since.

    Args:
        ctx: The MCP context, used to ask the user.
        plan_id: YNAB plan id or 'last-used'.
        book: The journal, to mark the operation undone.
        entry: The operation to undo.
        confirmation: A code from a previous preview, or None.

    Returns:
        What was done, or what to return instead when the user did not agree.
    """
    month, changes = entry.details["month"], entry.details["changes"]
    current = {c["id"]: c for c in await client.get_month_categories(plan_id, month)}
    moved = [
        change["category_id"]
        for change in changes
        if current.get(change["category_id"], {}).get("budgeted") != change["to"]
    ]
    if moved:
        conflict = writes.Plan(conflicts=moved)
        return result_of("nothing_to_do", "An amount changed since: both left alone.", conflict)
    question = _move_back_question(current, changes, month)
    if (refused := await _confirm_undo(ctx, plan_id, entry, question, confirmation)) is not None:
        return refused
    for change in reversed(changes):
        previous = client.milliunit_to_amount(change["from"])
        await client.set_category_budgeted(plan_id, month, change["category_id"], previous)
    return _undone(book, entry, "Both amounts restored.")


async def _undo_create(
    ctx: Context,
    plan_id: str,
    book: journal.Journal,
    entry: journal.Entry,
    confirmation: str | None,
) -> WriteResult | InputRequiredResult:
    """Delete the transactions an operation created, those still there.

    Args:
        ctx: The MCP context, used to ask the user.
        plan_id: YNAB plan id or 'last-used'.
        book: The journal, to mark the operation undone.
        entry: The operation to undo.
        confirmation: A code from a previous preview, or None.

    Returns:
        What was done, the ids already gone as conflicts, or what to return instead
        when the user did not agree.
    """
    created = entry.details["transaction_ids"]
    live = {tx["id"] for tx in await client.get_transactions(plan_id) if not tx.get("deleted")}
    present = [tx_id for tx_id in created if tx_id in live]
    gone = [tx_id for tx_id in created if tx_id not in live]
    if not present:
        return result_of(
            "nothing_to_do", "Already deleted: nothing to undo.", writes.Plan(conflicts=gone)
        )
    question = f"Undo: delete the {len(present)} transaction(s) this operation created?"
    if (refused := await _confirm_undo(ctx, plan_id, entry, question, confirmation)) is not None:
        return refused
    for tx_id in present:
        await client.delete_transaction(plan_id, tx_id)
    return _undone(book, entry, "Created transactions deleted.", gone)


async def _undo_flag(
    ctx: Context,
    plan_id: str,
    book: journal.Journal,
    entry: journal.Entry,
    confirmation: str | None,
) -> WriteResult | InputRequiredResult:
    """Put flags back to their previous colour, except those changed since.

    Args:
        ctx: The MCP context, used to ask the user.
        plan_id: YNAB plan id or 'last-used'.
        book: The journal, to mark the operation undone.
        entry: The operation to undo.
        confirmation: A code from a previous preview, or None.

    Returns:
        What was done, the flags changed since as conflicts, or what to return instead when
        the user did not agree.
    """
    now = {tx["id"]: flags.current(tx) for tx in await client.get_transactions(plan_id)}
    changes = entry.details["changes"]
    back = [
        c for c in changes if c["transaction_id"] in now and now[c["transaction_id"]] == c["to"]
    ]
    moved = [c["transaction_id"] for c in changes if c not in back]
    if not back:
        conflict = writes.Plan(conflicts=moved)
        return result_of("nothing_to_do", "Every flag changed since: left alone.", conflict)
    question = f"Undo: put back the flag of {len(back)} transaction(s)?"
    if (refused := await _confirm_undo(ctx, plan_id, entry, question, confirmation)) is not None:
        return refused
    await client.set_flags(plan_id, [(c["transaction_id"], c["from"]) for c in back])
    return _undone(book, entry, "Flags restored.", moved)


async def _undo_target(
    ctx: Context,
    plan_id: str,
    book: journal.Journal,
    entry: journal.Entry,
    confirmation: str | None,
) -> WriteResult | InputRequiredResult:
    """Put a category's target back, unless it changed since.

    Args:
        ctx: The MCP context, used to ask the user.
        plan_id: YNAB plan id or 'last-used'.
        book: The journal, to mark the operation undone.
        entry: The operation to undo.
        confirmation: A code from a previous preview, or None.

    Returns:
        What was done, the category as a conflict when its target changed since, or what
        to return instead when the user did not agree.
    """
    details = entry.details
    category = next(
        (c for c in await client.get_categories(plan_id) if c["id"] == details["category_id"]),
        None,
    )
    if category is None or targets.describe(category) != details["after"]:
        conflict = writes.Plan(conflicts=[details["category_id"]])
        return result_of("nothing_to_do", "The target changed since: left alone.", conflict)
    question = f"Undo: set the target of {untrusted(category['name'])} back?"
    if (refused := await _confirm_undo(ctx, plan_id, entry, question, confirmation)) is not None:
        return refused
    await client.set_category_target(plan_id, details["category_id"], details["undo"])
    return _undone(book, entry, "Target restored.")


async def _undo_payee(
    ctx: Context,
    plan_id: str,
    book: journal.Journal,
    entry: journal.Entry,
    confirmation: str | None,
) -> WriteResult | InputRequiredResult:
    """Give a renamed payee its old name back, unless it was renamed again since.

    Args:
        ctx: The MCP context, used to ask the user.
        plan_id: YNAB plan id or 'last-used'.
        book: The journal, to mark the operation undone.
        entry: The operation to undo.
        confirmation: A code from a previous preview, or None.

    Returns:
        What was done, the payee as a conflict when its name changed since, or what to
        return instead when the user did not agree.
    """
    details = entry.details
    payee = next(
        (p for p in await client.get_payees(plan_id) if p["id"] == details["payee_id"]),
        None,
    )
    if payee is None or payee["name"] != details["to"]:
        conflict = writes.Plan(conflicts=[details["payee_id"]])
        return result_of("nothing_to_do", "The payee was renamed since: left alone.", conflict)
    question = f"Undo: name the payee {untrusted(details['from'])!r} again?"
    if (refused := await _confirm_undo(ctx, plan_id, entry, question, confirmation)) is not None:
        return refused
    await client.rename_payee(plan_id, details["payee_id"], details["from"])
    return _undone(book, entry, "The payee's previous name is back.")
