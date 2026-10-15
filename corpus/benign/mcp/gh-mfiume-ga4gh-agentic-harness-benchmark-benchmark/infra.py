"""Failures that are the infrastructure's, not the model's: a row with one is not scored and reruns."""

from __future__ import annotations

import re
from typing import Any

# The registry itself unreachable (a DNS or network blip): every service lookup fails with it.
REGISTRY_DOWN = re.compile(r"registry endpoint \S+ unavailable")


def turn_hit(turn: dict[str, Any]) -> bool:
    return any(REGISTRY_DOWN.search(c.get("head") or "") for c in turn.get("tool_calls") or [])


def row_hit(row: dict[str, Any]) -> bool:
    return bool(row.get("infra_affected")) or any(turn_hit(t) for t in row.get("turns") or [])
