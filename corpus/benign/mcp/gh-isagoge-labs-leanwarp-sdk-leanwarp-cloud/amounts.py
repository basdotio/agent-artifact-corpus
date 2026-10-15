"""Exact workspace spending limits shared by Python, CLI and MCP."""

from __future__ import annotations

import re


def validate_spending_cap(value: int | None) -> None:
    if value is not None and (type(value) is not int or not 0 <= value <= 10**12):
        raise ValueError("max_spend_microusd must be an integer from 0 to 1000000000000, or None")


def usd_spending_cap(value: str) -> int:
    """Parse decimal USD without floating-point rounding or silent precision loss."""
    match = re.fullmatch(r"(0|[1-9][0-9]{0,6})(?:\.([0-9]{1,6}))?", value.strip())
    if match is None:
        raise ValueError("enter a USD amount from 0 to 1000000 with up to six decimals")
    result = int(match[1]) * 1_000_000 + int((match[2] or "").ljust(6, "0"))
    validate_spending_cap(result)
    return result
