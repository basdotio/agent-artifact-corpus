# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Net worth month by month, read-only."""

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import Field

from avenir_mcp import app, client, networth
from avenir_mcp.app import mcp

logger = logging.getLogger(__name__)


@mcp.tool(
    annotations={
        "title": "Net worth month by month",
        "read_only_hint": True,
        "idempotent_hint": True,
        "open_world_hint": True,
    }
)
async def get_net_worth_trend(
    plan_id: str,
    months_count: Annotated[int, Field(ge=1, le=networth.MAX_MONTHS)] = 12,
) -> networth.NetWorthTrend:
    """Assets, debts and net worth at the end of each month, to see debts go down.

    Use it for "is my debt going down?", "am I paying off my loans?" or "how did my net
    worth change over the year?". Every account counts, tracking ones included: credit
    cards, lines of credit, loans, mortgages and other liabilities are debts; every other
    account is an asset. A closed account counts for the months it still had a balance.
    Each month end is today's balance less the transactions dated after it; the current
    month shows today's balances. Amounts in currency units; debts are negative, as YNAB
    shows them, and net_worth is assets plus debts. For each account's balance today use
    list_accounts; for the months ahead, forecast_balance. Two YNAB requests: accounts,
    transactions; changes nothing.

    Args:
        plan_id: YNAB plan id or 'last-used'.
        months_count: Number of months to show, the current one included, 1 to 24
            (default 12).

    Returns:
        The month ends, oldest first, and how the net worth changed over them.
    """
    logger.info("Tool called: get_net_worth_trend(months_count=%d)", months_count)
    return networth.trend(
        await client.get_accounts(plan_id),
        await client.get_transactions(plan_id),
        app.today(),
        months_count,
    )
