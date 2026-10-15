# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""How much of the income was kept, month by month, read-only."""

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import Field

from avenir_mcp import app, client, savings
from avenir_mcp.app import mcp

logger = logging.getLogger(__name__)


@mcp.tool(
    annotations={
        "title": "Savings rate month by month",
        "read_only_hint": True,
        "idempotent_hint": True,
        "open_world_hint": True,
    }
)
async def get_savings_rate(
    plan_id: str,
    months_count: Annotated[int, Field(ge=1, le=savings.MAX_MONTHS)] = 6,
) -> savings.SavingsRate:
    """How much of the income was kept, month by month: income, spending, saved, rate.

    Use it for "what's my savings rate?", "how much do I put aside each month?" or "am
    I saving more than last spring?". Income is money in categorised to Ready to Assign
    on the budget accounts; starting balances and transfers are not income. Spending is
    money out of the budget accounts less refunds (money in categorised to a spending
    category); transfers between budget accounts are left out, a transfer to a tracking
    account holding an asset (savings, investments) is saved, a transfer to a tracking
    loan is spending. Saved is income plus spending; rate is saved over income, in
    percent, null for a month without income. Complete months only, from the budget's
    first transaction. Relay the notes with the figures. Amounts in currency units,
    spending negative. For spending per category use get_spending_trends. Three YNAB
    requests: accounts, categories, transactions; changes nothing.

    Args:
        plan_id: YNAB plan id or 'last-used'.
        months_count: Complete months to measure, before the current one, 1 to 24
            (default 6).

    Returns:
        Each month's income, spending, saved and rate, the same over the period, the best
        and worst months, and how they were counted.
    """
    logger.info("Tool called: get_savings_rate(months_count=%d)", months_count)
    return savings.summary(
        await client.get_accounts(plan_id),
        await client.get_categories(plan_id),
        await client.get_transactions(plan_id),
        app.today(),
        months_count,
    )
