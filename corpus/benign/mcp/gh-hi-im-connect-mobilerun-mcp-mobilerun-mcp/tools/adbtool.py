"""Raw adb passthrough. Off unless MOBILERUN_MCP_ENABLE_ADB=1, and refused while a safety policy is on."""

from __future__ import annotations

import shlex

from fastmcp import FastMCP

from ..adb import AdbError
from ..errors import fail
from ..session import Runtime
from .common import Device, get_session

MAX_OUTPUT = 20_000
TIMEOUT = 60.0
BLOCKED_GLOBALS = {"-s", "-H", "-P", "-L", "-a", "-d", "-e"}

DESCRIPTION = (
    "Run an adb command against the device. Write exactly what you would type after `adb`, e.g. "
    "`shell dumpsys window | grep mCurrentFocus`, `logcat -d -t 100`, `shell pm list packages -3`. "
    "For `shell ...` the rest goes to the device shell (pipes work). It bypasses every safety check "
    "of the other tools, so never use it to reach something a tool refused. Output is truncated."
)


def split_command(command: str) -> list[str]:
    """``shell <rest>`` keeps <rest> as one argument for the device shell; others are shlex-split."""
    stripped = command.strip()
    if stripped == "shell":
        fail("invalid_argument", "shell needs a command")
    if stripped.startswith("shell "):
        return ["shell", stripped[len("shell ") :]]
    parts = shlex.split(stripped)
    if not parts:
        fail("invalid_argument", "command is empty")
    if parts[0] in BLOCKED_GLOBALS:
        fail("not_permitted", f"global adb option {parts[0]} is not allowed; the device is fixed")
    return parts


def register(mcp: FastMCP, rt: Runtime) -> None:
    @mcp.tool(
        name="aura-adb",
        description=DESCRIPTION + " (AURA's name for the adb tool.)",
        tags={"write"},
    )
    async def aura_adb(command: str, device: Device = None) -> dict:
        return await adb_command(command, device)

    @mcp.tool(name="adb", description=DESCRIPTION, tags={"write"})
    async def adb_command(command: str, device: Device = None) -> dict:
        if rt.config.policy != "off":
            fail(
                "policy_blocked",
                "adb bypasses the safety policy",
                "unset MOBILERUN_MCP_POLICY to use it",
            )
        session = get_session(rt, device)
        argv = split_command(command)
        try:
            result = await session.adb.run(*argv, timeout=TIMEOUT, check=False)
        except AdbError as exc:
            fail("device_unreachable", str(exc))
        text = "\n".join(filter(None, (result.stdout, result.stderr))).strip() or "(no output)"
        truncated = len(text) > MAX_OUTPUT
        return {
            "ok": result.ok,
            "returncode": result.returncode,
            "output": text[:MAX_OUTPUT]
            + (f"\n...(truncated, {len(text) - MAX_OUTPUT} more chars)" if truncated else ""),
        }
