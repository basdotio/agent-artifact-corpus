# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Flag transactions for the user to look at, after confirmation, and undo it."""

from __future__ import annotations

import logging

from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp.types import InputRequiredResult

from avenir_mcp import client, journal
from avenir_mcp.app import WRITE_TAG, mcp
from avenir_mcp.confirm import WriteStatus, gate, merged
from avenir_mcp.flags import Flag, FlagChange, plan_flags
from avenir_mcp.model import Model

logger = logging.getLogger(__name__)


class FlagResult(Model):
    """The outcome of flag_transactions."""

    status: WriteStatus
    """Outcome: applied, confirmation_required (nothing changed yet; pass the code back once the
    user agrees), declined (the user said no), or nothing_to_do.
    """
    message: str
    """What happened and what to do next, for the agent to relay."""
    changes: list[FlagChange]
    """Every transaction whose flag changes: before and after."""
    unchanged_count: int
    """Flags asked for that the transaction already has, skipped."""
    confirmation: str | None
    """Single-use code confirming exactly this preview, valid 10 minutes; null unless status is
    confirmation_required.
    """
    operation_id: str | None
    """Journal id of the applied operation, for undo_operation; null unless status is applied."""


def _name(color: str | None) -> str:
    """Name a colour as the user reads it.

    Args:
        color: A flag colour, or None.

    Returns:
        Its name, or "none".
    """
    return color or "none"


def question(changes: list[FlagChange], head: str) -> str:
    """Write the question put to the user: one line per transaction.

    Args:
        changes: The flags that change.
        head: The first line.

    Returns:
        The question.
    """
    lines = [
        f"- {c.date} {c.payee} {c.amount:.2f}: {_name(c.from_color)} → {_name(c.to_color)}"
        for c in changes
    ]
    return "\n".join([head, *lines])


@mcp.tool(
    tags={WRITE_TAG},
    annotations={
        "title": "Flag transactions",
        "read_only_hint": False,
        "destructive_hint": False,
        "idempotent_hint": True,
        "open_world_hint": True,
    },
)
async def flag_transactions(
    plan_id: str,
    flags: list[Flag],
    ctx: Context,
    confirmation: str | None = None,
) -> FlagResult | InputRequiredResult:
    """Set or remove the coloured flag of transactions, after the user confirms.

    Use it to mark what the user should look at in YNAB rather than deciding for
    them: a possible duplicate, a charge they do not recognise, a refund to watch
    for. Colours: red, orange, yellow, green, blue, purple; null removes the flag.
    The user may have named their flags in YNAB: ask which colour means what
    before choosing. A flag already set is left out. Undoable with undo_operation.
    Confirmation works as for apply_categories.

    Args:
        plan_id: YNAB plan id or 'last-used'.
        flags: {transaction_id, color} pairs, one per transaction.
        ctx: The MCP context, used to ask the user.
        confirmation: Code from a previous "confirmation_required" result.

    Returns:
        Every flag before and after, and what was done, or an input request the client answers
        by asking the user (protocol 2026-07-28).

    Raises:
        ToolError: If no flag is given, a transaction is named twice or is not in the plan,
            or the confirmation code is refused.
    """
    logger.info("Tool called: flag_transactions(n=%d)", len(flags))
    try:
        plan = plan_flags(await client.get_transactions(plan_id), flags)
    except ValueError as error:
        raise ToolError(str(error)) from error
    result = FlagResult(
        status="applied",
        message="",
        changes=plan.changes,
        unchanged_count=plan.unchanged_count,
        confirmation=None,
        operation_id=None,
    )
    if not plan.changes:
        return result.model_copy(
            update={"status": "nothing_to_do", "message": "Every flag is already as asked."}
        )
    head = f"Change the flag of {len(plan.changes)} transaction(s)?"
    subject = {"flags": [(c.transaction_id, c.to_color) for c in plan.changes]}
    stop = await gate(ctx, plan_id, subject, question(plan.changes, head), confirmation)
    if stop is not None:
        return stop if isinstance(stop, InputRequiredResult) else merged(result, stop)
    await client.set_flags(plan_id, [(c.transaction_id, c.to_color) for c in plan.changes])
    operation_id = journal.Journal(journal.default_path()).record(
        plan_id,
        "flag",
        [],
        {
            "changes": [
                {"transaction_id": c.transaction_id, "from": c.from_color, "to": c.to_color}
                for c in plan.changes
            ]
        },
    )
    return result.model_copy(
        update={
            "message": f"Flagged. undo_operation with operation_id {operation_id} puts them back.",
            "operation_id": operation_id,
        }
    )
