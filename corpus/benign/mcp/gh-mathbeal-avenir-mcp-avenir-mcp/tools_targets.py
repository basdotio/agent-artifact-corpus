# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Set, change or remove a category's target, after confirmation, and undo it."""

from __future__ import annotations

import logging
from datetime import date
from typing import Annotated

from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp.types import InputRequiredResult
from pydantic import Field

from avenir_mcp import client, journal, targets
from avenir_mcp.amounts import Amount
from avenir_mcp.app import WRITE_TAG, mcp
from avenir_mcp.confirm import WriteStatus, gate, merged
from avenir_mcp.model import Model
from avenir_mcp.text import untrusted

logger = logging.getLogger(__name__)


class TargetChange(Model):
    """The outcome of set_category_target."""

    status: WriteStatus
    """Outcome: applied, confirmation_required (nothing changed yet; pass the code back once the
    user agrees), declined (the user said no), or nothing_to_do.
    """
    message: str
    """What happened and what to do next, for the agent to relay."""
    category: str
    """Category name."""
    before: str
    """The target before, e.g. "no target" or "50.00 each month"."""
    after: str
    """The target after."""
    undoable: bool
    """False when YNAB's API cannot bring the previous target back; the user is told first."""
    confirmation: str | None
    """Single-use code confirming exactly this preview, valid 10 minutes; null unless status is
    confirmation_required.
    """
    operation_id: str | None
    """Journal id of the applied operation, for undo_operation; null unless status is applied."""


def _warning(before: str) -> str:
    """Say that undo cannot restore a target the API cannot set.

    Args:
        before: The previous target, as the user reads it.

    Returns:
        The warning, naming it.
    """
    return f"undo_operation cannot bring back the previous target ({before}): only YNAB can."


@mcp.tool(
    tags={WRITE_TAG},
    annotations={
        "title": "Set a category's target",
        "read_only_hint": False,
        "destructive_hint": True,
        "idempotent_hint": True,
        "open_world_hint": True,
    },
)
async def set_category_target(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    plan_id: str,
    category_id: str,
    ctx: Context,
    amount: Annotated[
        Amount | None,
        Field(description="Target amount in currency units, greater than 0; omit to remove it."),
    ] = None,
    by_date: date | None = None,
    frequency: targets.Frequency | None = None,
    confirmation: str | None = None,
) -> TargetChange | InputRequiredResult:
    """Set, change or remove a category's target, after the user confirms.

    A target YNAB tracks for the category: an amount to reach by a date (a holiday
    fund, a yearly tax), or an amount to set aside each month, week or year. Give
    either by_date or frequency, not both; with neither, an existing target keeps its
    kind and only its amount changes (a new one is monthly). No amount removes the
    target. Undo restores the previous target, except one set in YNAB's app as monthly
    funding, a target balance or a debt payment when it is replaced or removed: the
    user is told before confirming. Confirmation works as for apply_categories.

    Args:
        plan_id: YNAB plan id or 'last-used'.
        category_id: Category (from get_category_balances or list_category_groups).
        ctx: The MCP context, used to ask the user.
        amount: Target amount in currency units, greater than 0; omit to remove it.
        by_date: YYYY-MM-DD to reach the amount by.
        frequency: monthly, weekly or yearly: the amount to set aside that often.
        confirmation: Code from a previous "confirmation_required" result.

    Returns:
        The target before and after, whether undo can restore it, or an input request the
        client answers by asking the user (protocol 2026-07-28).

    Raises:
        ToolError: If the category is not in the plan, the change is one YNAB would refuse,
            or the confirmation code is refused.
    """
    logger.info("Tool called: set_category_target")
    category = next(
        (c for c in await client.get_categories(plan_id) if c["id"] == category_id), None
    )
    if category is None:
        raise ToolError(
            f"Category {category_id} is not in this plan: use a category_id from "
            "get_category_balances or list_category_groups."
        )
    try:
        change = targets.plan(
            category,
            amount=amount,
            date=by_date.isoformat() if by_date else None,
            frequency=frequency,
        )
    except ValueError as error:
        raise ToolError(str(error)) from error
    result = TargetChange(
        status="applied",
        message="",
        category=untrusted(category["name"]),
        before=change.before,
        after=change.after,
        undoable=change.undo is not None,
        confirmation=None,
        operation_id=None,
    )
    if change.unchanged:
        return result.model_copy(
            update={"status": "nothing_to_do", "message": "The target is already that one."}
        )
    question = f"Set the target of {result.category}: {change.before} → {change.after}?"
    if change.undo is None:
        question += "\n" + _warning(change.before)
    subject = {"category": category_id, "fields": change.fields}
    stop = await gate(ctx, plan_id, subject, question, confirmation)
    if stop is not None:
        return stop if isinstance(stop, InputRequiredResult) else merged(result, stop)
    await client.set_category_target(plan_id, category_id, change.fields)
    if change.undo is None:
        return result.model_copy(update={"message": f"Target set. {_warning(change.before)}"})
    operation_id = journal.Journal(journal.default_path()).record(
        plan_id,
        "target",
        [],
        {"category_id": category_id, "undo": change.undo, "after": change.after},
    )
    return result.model_copy(
        update={
            "message": f"Target set. undo_operation with operation_id {operation_id} restores it.",
            "operation_id": operation_id,
        }
    )
