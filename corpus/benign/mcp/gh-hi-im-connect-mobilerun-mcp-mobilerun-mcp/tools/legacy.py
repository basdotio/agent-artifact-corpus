"""Tools kept from the first version of this server."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from fastmcp import FastMCP

from ..errors import fail
from ..observe import mutate
from ..session import Runtime
from .common import Device, get_session

KEYS = ("home", "back", "enter")
GOAL = re.compile(r"(Goal (?:achieved|failed): .*)")


def _mobilerun_bin(configured: str | None) -> str:
    return configured or shutil.which("mobilerun") or str(Path.home() / ".local/bin/mobilerun")


def register(mcp: FastMCP, rt: Runtime) -> None:
    @mcp.tool(tags={"write"})
    async def press(button: str, device: Device = None) -> dict:
        """Press home, back or enter (kept for old clients; prefer press_home/back/enter)."""
        if button not in KEYS:
            fail("invalid_argument", "button must be home, back or enter")
        session = get_session(rt, device)
        return await mutate(session, lambda: session.press(button), {"action": f"press_{button}"})
