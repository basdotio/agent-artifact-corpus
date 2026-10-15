# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""The MCP server instance and what decides which tools it exposes."""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from datetime import date

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.transforms import GetToolNext, Transform, VersionSpec
from fastmcp.tools import Tool

from avenir_mcp import __version__

# The version clients see in the initialize answer: avenir-mcp's, not FastMCP's.
mcp = FastMCP("avenir-mcp", version=__version__)


# Tools that change a plan carry this tag; read-only mode hides them.
WRITE_TAG = "write"

# Per tool, a sentence of its description that names a write tool, and the sentence
# that replaces it while writes are off, so no description points to a hidden tool.
_READ_ONLY_WORDING: dict[str, tuple[str, str]] = {}


def set_read_only_wording(tool: str, sentence: str, replacement: str) -> None:
    """Declare how a tool's description reads while writes are off.

    Args:
        tool: The tool's name.
        sentence: A sentence of its description that names a write tool.
        replacement: What the description says instead in read-only mode.
    """
    _READ_ONLY_WORDING[tool] = (sentence, replacement)


class _WriteGate(Transform):
    """Hide the write tools, from the list and from calls, unless writes are enabled.

    One gate for the server's lifetime: configure opens or closes it. FastMCP's own
    enable and disable add a filter per call instead, which piles up.
    """

    def __init__(self) -> None:
        """Start closed: read-only until configured otherwise."""
        self.open = False

    def _hidden(self, tool: Tool) -> bool:
        """Say whether this tool is a write tool while writes are off.

        Args:
            tool: A tool of the server.

        Returns:
            True when the gate is closed and the tool writes.
        """
        return not self.open and WRITE_TAG in tool.tags

    def _worded(self, tool: Tool) -> Tool:
        """Give the tool as the client sees it: read-only wording while writes are off.

        Args:
            tool: A visible tool of the server.

        Returns:
            The tool, or a copy whose description names no write tool.
        """
        if self.open or tool.name not in _READ_ONLY_WORDING:
            return tool
        sentence, replacement = _READ_ONLY_WORDING[tool.name]
        description = (tool.description or "").replace(sentence, replacement)
        return tool.model_copy(update={"description": description})

    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        """List the tools, less the write tools while writes are off.

        Args:
            tools: The server's tools.

        Returns:
            Those the client may see, worded for the mode.
        """
        return [self._worded(tool) for tool in tools if not self._hidden(tool)]

    async def get_tool(
        self, name: str, call_next: GetToolNext, *, version: VersionSpec | None = None
    ) -> Tool | None:
        """Find a tool, as if a write tool did not exist while writes are off.

        Args:
            name: The tool asked for.
            call_next: The lookup this gate wraps.
            version: The version asked for, if any.

        Returns:
            The tool, worded for the mode, or None when it is unknown or hidden.
        """
        tool = await call_next(name, version=version)
        return None if tool is None or self._hidden(tool) else self._worded(tool)


_GATE = _WriteGate()
mcp.add_transform(_GATE)


def configure(enable_writes: bool) -> None:
    """Expose write tools only when enabled; otherwise they are neither listed nor callable.

    Args:
        enable_writes: True to register the write tools.
    """
    _GATE.open = enable_writes


def today() -> date:
    """Give today's date; a function so tests can fix it.

    Returns:
        Today, in the machine's time zone.
    """
    return date.today()


_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-01$")


def check_month(month: str) -> None:
    """Refuse a malformed month before YNAB answers with a bare 404.

    Args:
        month: 'current', or the first day of a month as YYYY-MM-01.

    Raises:
        ToolError: If the month is neither, saying the expected format.
    """
    if month != "current" and not _MONTH.match(month):
        raise ToolError(
            f"month must be 'current' or the first day of a month as YYYY-MM-01, got {month!r}."
        )


def resolve_month(month: str) -> str:
    """Turn 'current' into the actual month, so a journaled change names its month.

    Args:
        month: 'current', or the first day of a month as YYYY-MM-01.

    Returns:
        The month as YYYY-MM-01.
    """
    return f"{today():%Y-%m}-01" if month == "current" else month


class QuietToolErrors(logging.Filter):  # pylint: disable=too-few-public-methods
    """Log an expected ToolError on one line; keep tracebacks for real failures.

    FastMCP logs every tool error with its traceback. A ToolError is a message
    written for the agent (a malformed month, an unknown account), not a crash.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Shorten a ToolError's record to one line; leave other records as they are.

        Args:
            record: The log record about to be emitted.

        Returns:
            Always True: no record is dropped.
        """
        if record.exc_info and isinstance(record.exc_info[1], ToolError):
            record.msg = f"{record.getMessage()}: {record.exc_info[1]}"
            record.args = None
            record.exc_info = None
            record.exc_text = None
        return True


logging.getLogger("fastmcp.server.server").addFilter(QuietToolErrors())
