# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""YNAB's Age of Money, month by month, read-only."""

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import Field

from avenir_mcp import age, app, client
from avenir_mcp.app import mcp

logger = logging.getLogger(__name__)


@mcp.tool(
    annotations={
        "title": "Age of Money month by month",
        "read_only_hint": True,
        "idempotent_hint": True,
        "open_world_hint": True,
    }
)
async def get_age_of_money(
    plan_id: str,
    months_count: Annotated[int, Field(ge=1, le=age.MAX_MONTHS)] = 12,
) -> age.AgeOfMoney:
    """YNAB's Age of Money: how old the money spent is today, and its trend month by month.

    Use it for "how old is my money?", "am I living on last month's income?" or "is my
    buffer growing?". The figure is YNAB's own, in days: how long, on average, money
    stayed in the budget accounts before being spent, the oldest money spent first. Over
    30 days means living on last month's income. The answer gives each month's figure up
    to the current one, the latest, the change and its direction over the period; a month
    is null when YNAB had not enough history. Relay the notes with the figures. For how
    long the money would last without income use get_runway. One YNAB request, the list
    of months; changes nothing.

    Args:
        plan_id: YNAB plan id or 'last-used'.
        months_count: Months to show, the current one included, 1 to 24 (default 12).

    Returns:
        Each month's Age of Money in days, the latest, the change over the period, and
        how YNAB counts it.
    """
    logger.info("Tool called: get_age_of_money(months_count=%d)", months_count)
    return age.summary(await client.get_months(plan_id), app.today(), months_count)
