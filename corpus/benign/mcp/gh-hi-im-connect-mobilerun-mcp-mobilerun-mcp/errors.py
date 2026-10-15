"""Structured tool errors: ``[code] message (hint)`` so clients can branch on the code."""

from __future__ import annotations

from typing import NoReturn

from fastmcp.exceptions import ToolError

CODES = (
    "device_unreachable",
    "policy_blocked",
    "stale_som_id",
    "unknown_som_id",
    "element_not_found",
    "app_not_found",
    "timeout",
    "unsupported",
    "invalid_argument",
    "not_permitted",
    "plan_incomplete",
)


class McpToolError(ToolError):
    def __init__(self, code: str, message: str, hint: str | None = None) -> None:
        self.code = code
        text = f"[{code}] {message}"
        if hint:
            text += f" (hint: {hint})"
        super().__init__(text)


def fail(code: str, message: str, hint: str | None = None) -> NoReturn:
    raise McpToolError(code, message, hint)
