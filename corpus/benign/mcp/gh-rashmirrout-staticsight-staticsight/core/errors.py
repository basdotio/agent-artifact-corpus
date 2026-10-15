"""Error types rendered as Markdown cards instead of crashing the server."""

from __future__ import annotations


class StaticSightError(Exception):
    """Base error rendered as a Markdown card instead of crashing the server."""

    title = "StaticSight error"

    def __init__(self, message: str, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.hint = hint


class ToolMissing(StaticSightError):
    title = "Required CLI tool is not installed"

    def __init__(self, tool: str, hint: str | None = None):
        super().__init__(f"`{tool}` was not found on PATH.", hint)
        self.tool = tool


class ToolFailed(StaticSightError):
    title = "CLI tool failed"


class ToolTimeout(StaticSightError):
    title = "CLI tool timed out"


class InvalidArgument(StaticSightError):
    title = "Invalid argument"
