# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Amounts an agent may pass: finite, and within what a household budget can hold."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

MAX_AMOUNT = 1_000_000_000

Amount = Annotated[
    float,
    Field(
        allow_inf_nan=False,
        ge=-MAX_AMOUNT,
        le=MAX_AMOUNT,
        description="In currency units, negative for money out; at most a billion either way.",
    ),
]
"""An amount in currency units, checked by the tool's argument schema before any call."""
