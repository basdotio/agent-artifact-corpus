from __future__ import annotations


class MCPError(Exception):
    """Expected, user-actionable MCP error with a stable machine-readable code."""

    def __init__(self, message: str, code: str = "ERROR", *, recoverable: bool = True):
        super().__init__(message)
        self.code = code
        self.recoverable = recoverable
