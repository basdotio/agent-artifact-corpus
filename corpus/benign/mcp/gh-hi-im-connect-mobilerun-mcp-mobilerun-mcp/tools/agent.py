"""The mobilerun agent's action set (mobilerun/agent/utils/signatures.py) as MCP tools.

Element indices come from get_state, which numbers the screen exactly like the mobilerun agent
(see :mod:`mobilerun_mcp.agentui`), so actions written for mobilerun carry over unchanged.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import yaml
from fastmcp import FastMCP

from ..errors import fail
from ..observe import mutate
from ..parsers.packages import resolve_app
from ..session import Runtime
from .apps import launch
from .common import Device, get_session, guard_foreground
from .input import index_point, tap_point

BUTTONS = ("back", "home", "enter")
MAX_WAIT = 60.0
DEFAULT_CREDENTIALS = ("config/credentials.yaml", "~/.config/mobilerun/credentials.yaml")


def load_secrets(path: str | None = None) -> dict[str, str]:
    """mobilerun's credentials file: ``secrets: {ID: {value, enabled} | "value"}``."""
    candidates = [path] if path else [os.environ.get("MOBILERUN_CREDENTIALS"), *DEFAULT_CREDENTIALS]
    for candidate in filter(None, candidates):
        file = Path(candidate).expanduser()
        if file.is_file():
            data = yaml.safe_load(file.read_text()) or {}
            secrets = {}
            for key, item in (data.get("secrets") or {}).items():
                if isinstance(item, dict):
                    value, enabled = item.get("value", ""), item.get("enabled", True)
                else:
                    value, enabled = item, True
                if enabled and isinstance(value, str) and value.strip():
                    secrets[str(key)] = value
            return secrets
    return {}


def register(mcp: FastMCP, rt: Runtime) -> None:
    @mcp.tool(tags={"read"})
    async def get_state(device: Device = None) -> dict:
        """The screen as the mobilerun agent sees it: phone state plus numbered UI elements
        ('index. className: resourceId, text - (x1,y1,x2,y2)'). Use the indices with click,
        long_press(index=), type(index=) and type_secret."""
        session = get_session(rt, device)
        text = await session.agent_state()
        return {"state": text, "element_count": len(session.agent_elements)}

    async def tap_at(device: Device, x: int, y: int, info: dict, action: str) -> dict:
        session = get_session(rt, device)
        await guard_foreground(rt, session)
        return await mutate(session, lambda: tap_point(session, x, y), {"action": action, **info})

    @mcp.tool(tags={"write"})
    async def click(index: int, device: Device = None) -> dict:
        """Click the get_state element with this index (its center, avoiding views drawn on top)."""
        session = get_session(rt, device)
        x, y, info = await index_point(session, index)
        return await tap_at(device, x, y, info, "click")

    @mcp.tool(tags={"write"})
    async def click_at(x: int, y: int, device: Device = None) -> dict:
        """Click at screen position (x, y)."""
        return await tap_at(device, x, y, {"target": {"x": x, "y": y}}, "click_at")

    @mcp.tool(tags={"write"})
    async def click_area(x1: int, y1: int, x2: int, y2: int, device: Device = None) -> dict:
        """Click the center of the area (x1, y1, x2, y2)."""
        x, y = (x1 + x2) // 2, (y1 + y2) // 2
        return await tap_at(device, x, y, {"target": {"area": [x1, y1, x2, y2]}}, "click_area")

    @mcp.tool(tags={"write"})
    async def system_button(button: str, device: Device = None) -> dict:
        """Press a system button: back, home or enter."""
        name = button.strip().lower()
        if name not in BUTTONS:
            fail("invalid_argument", f"button must be one of {', '.join(BUTTONS)}")
        session = get_session(rt, device)
        return await mutate(session, lambda: session.press(name), {"action": f"press_{name}"})

    @mcp.tool(tags={"read"})
    async def wait(duration: float = 1.0) -> dict:
        """Wait for duration seconds (max 60)."""
        seconds = min(max(duration, 0.0), MAX_WAIT)
        await asyncio.sleep(seconds)
        return {"ok": True, "waited": seconds}

    @mcp.tool(tags={"write"})
    async def open_app(text: str, device: Device = None) -> dict:
        """Open an app by name or package (mobilerun agent action)."""
        session = get_session(rt, device)
        apps = await session.apps()
        exact = next((a for a in apps if a.package == text), None)
        if exact:
            return await launch(rt, session, exact.package, exact.label)
        best, ranked = resolve_app(text, apps)
        if best is None:
            if not ranked:
                fail("app_not_found", f'no installed app matches "{text}"', "try list_apps")
            return {
                "ok": False,
                "ambiguous": True,
                "candidates": [{**a.to_dict(), "score": s} for a, s in ranked],
            }
        return await launch(rt, session, best.package, best.label)

    @mcp.tool(tags={"write"})
    async def complete(success: bool, message: str, device: Device = None) -> dict:
        """Finish the task (mobilerun agent action): success flag plus the result or the reason
        for failure. Recorded in the ledger like end_session."""
        session = get_session(rt, device)
        problem = session.ledger.end("success" if success else "failed")
        return {
            "ok": True,
            "success": success,
            "message": message,
            **({"warning": problem} if problem else {}),
            "ledger": session.ledger.to_dict(),
        }

    @mcp.tool(tags={"write"})
    async def type_secret(secret_id: str, index: int, device: Device = None) -> dict:
        """Type a secret from the mobilerun credentials file (MOBILERUN_CREDENTIALS, else
        config/credentials.yaml or ~/.config/mobilerun/credentials.yaml) into the get_state
        element index (-1 = the focused field). The value is never returned."""
        secrets = load_secrets()
        if secret_id not in secrets:
            fail(
                "invalid_argument",
                f"secret {secret_id!r} not found; available: {sorted(secrets)}",
                "add it under secrets: in the credentials file",
            )
        session = get_session(rt, device)
        if index != -1:
            x, y, _ = await index_point(session, index)
            await mutate(session, lambda: tap_point(session, x, y), {"action": "focus"})
        result = await mutate(
            session,
            lambda: session.input_text(secrets[secret_id]),
            {"action": "type_secret", "secret_id": secret_id},
        )
        return result
