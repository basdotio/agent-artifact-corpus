"""MCP tool definitions.

Same shape as the Harmony sibling, on purpose: activity-first, with buttons
and commands going through the running activity unless a device is named.

Models: the X1, X1S and X2 all work through sofabaton-x-server; the X2 can
also be reached over MQTT, alone or alongside the server (client.py picks the
path per call). So the model can plan around what a given hub can do,
get_status reports ``model``, ``capabilities`` and ``limitations``, and a tool
that can't run on this hub says why and what would enable it rather than
failing vaguely. The server instructions say the MQTT features are X2-only.

Docstrings are the model's documentation; signatures become JSON Schema.

Status: verified against the simulator only (see assumptions.py).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field
from typing_extensions import TypedDict

from .api import PressPage, ServerAPI
from .client import Outcome, Path, SofabatonClient, Status
from .config import ButtonName, load_settings
from .limits import MAX_DELAY_MS, MAX_REPEAT, MIN_DELAY_MS

log = logging.getLogger(__name__)

_client: SofabatonClient | None = None


def client() -> SofabatonClient:
    assert _client is not None, "server lifespan has not started"
    return _client


@asynccontextmanager
async def lifespan(_server: MCPServer) -> AsyncIterator[None]:
    """Open the HTTP pool and the MQTT connection (whichever are configured) once; close them at shutdown.

    sofabaton-x-server holds the hub session itself, so there's no hub connection
    to keep here; the MQTT broker connection is ours to keep.
    """
    global _client
    settings = load_settings()
    api = ServerAPI(settings.url) if settings.url else None
    _client = SofabatonClient(settings, api)
    await _client.start()
    try:
        yield
    finally:
        await _client.stop()
        _client = None


mcp = MCPServer(
    "sofabaton",
    instructions=(
        "Controls a Sofabaton universal remote hub (X1, X1S or X2). Call get_status first: it gives the hub's model, "
        "the running activity, and `capabilities` and `limitations` for this hub, so you know what will work. "
        "Prefer activities: start_activity powers the right devices; power_off turns the running activity off. "
        "press_button sends a remote button (VOL_UP, PAUSE, ...) through the running activity; send_command sends a "
        "named macro, favorite or device command. MQTT features (live activity state, control while the Sofabaton "
        "app is open) exist only on the X2; on an X1/X1S, close the Sofabaton app if commands are refused."
    ),
    lifespan=lifespan,
)

# Explicit annotations everywhere (a tool without them is assumed destructive,
# non-idempotent and open-world). open_world is False: everything is on the LAN.
# Nothing is destructive: this server can't edit the hub (see config.py).
_READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
_ACT = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)
_ACT_IDEMPOTENT = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)


class ActivityInfo(TypedDict):
    name: str
    running: bool


class DeviceInfo(TypedDict):
    name: str
    brand: str | None  # null over MQTT, which only gives names
    device_class: str | None


class CommandInfo(TypedDict):
    label: str
    kind: Literal["macro", "favorite", "device"]
    via: str  # "activity" (a macro) or the device a favorite goes to


class CommandList(TypedDict):
    source: str  # "activity Watch Shield" or "device Onkyo Receiver"
    commands: list[CommandInfo]


class ActionResult(TypedDict):
    outcome: Literal["done", "unchanged", "dry_run"]
    detail: str
    via: Path  # "server" (sofabaton-x-server) or "mqtt" (the X2 directly)
    sent: list[str]  # requests or publishes sent (or that would be, in dry-run); the MAC shows as <MAC>


def _result(o: Outcome, done: str, unchanged: str) -> ActionResult:
    if o.dry_run:
        return {"outcome": "dry_run", "detail": f"DRY RUN, nothing sent: would {done}", "via": o.via, "sent": o.sent}
    if o.changed:
        detail = done[0].upper() + done[1:] + (f". {o.note}" if o.note else "")
        return {"outcome": "done", "detail": detail, "via": o.via, "sent": o.sent}
    return {"outcome": "unchanged", "detail": unchanged, "via": o.via, "sent": []}


Target = Annotated[
    str | None,
    Field(description="An activity or device name. Omit to use the running activity."),
]
Repeat = Annotated[int, Field(ge=1, le=MAX_REPEAT, description=f"How many times to press it (1-{MAX_REPEAT}).")]
DelayMs = Annotated[
    int | None, Field(ge=MIN_DELAY_MS, le=MAX_DELAY_MS, description="Pause between repeats (default 300 ms).")
]


@mcp.tool(title="Get hub status", annotations=_READ)
async def get_status() -> Status:
    """Start here. The hub's model, running activity, and what it can do right now.

    capabilities lists what works on this hub now: catalog (the list_* tools), activities, buttons, commands,
    presses, find_remote, hub_info, and on an X2 over MQTT live_activity_state and control_while_app_open.
    limitations says what doesn't work and how to enable it. via is how commands would be sent: "server"
    (sofabaton-x-server, any model) or "mqtt" (X2 only). transition is non-null while an X2's power macro
    may still be running.
    """
    return await client().status()


@mcp.tool(title="List activities", annotations=_READ)
async def list_activities() -> list[ActivityInfo]:
    """List the activities set up on the hub, marking the running one."""
    return [{"name": n, "running": on} for n, on in await client().activities()]


@mcp.tool(title="List devices", annotations=_READ)
async def list_devices() -> list[DeviceInfo]:
    """List the devices the hub controls."""
    return [{"name": n, "brand": b, "device_class": c} for n, b, c in await client().devices()]


@mcp.tool(title="List commands", annotations=_READ)
async def list_commands(target: Target = None) -> CommandList:
    """List the named commands send_command accepts for an activity or device (default: the running activity).

    For an activity these are its macros and favorites; for a device, its own command list. The remote's hard
    buttons are separate: use press_button for those.
    """
    source, options = await client().commands(target)
    return {"source": source, "commands": [{"label": o.label, "kind": o.kind, "via": o.via} for o in options]}


@mcp.tool(title="Start an activity", annotations=_ACT_IDEMPOTENT)
async def start_activity(
    activity: Annotated[str, Field(description="Activity name from list_activities, e.g. 'Watch Shield'.")],
) -> ActionResult:
    """Start an activity and wait until the hub confirms it (its power-on macro can take a while).

    Starting the activity that is already running does nothing (outcome 'unchanged').
    """
    outcome, name = await client().start_activity(activity)
    return _result(outcome, f"start {name}", f"{name} was already running")


@mcp.tool(title="Turn the running activity off", annotations=_ACT_IDEMPOTENT)
async def power_off() -> ActionResult:
    """Power off the running activity and wait until the hub confirms."""
    outcome, name = await client().power_off()
    return _result(outcome, f"power off {name}", "Nothing was running")


@mcp.tool(title="Press a remote button", annotations=_ACT)
async def press_button(
    button: ButtonName, target: Target = None, repeat: Repeat = 1, delay_ms: DelayMs = None
) -> ActionResult:
    """Press one of the remote's hard buttons, e.g. VOL_UP with repeat=3, or PAUSE.

    Sent to the running activity by default, which routes it to the device it binds that button to. Rapid
    repeated calls are rate-limited.
    """
    outcome, where = await client().press(button, target, repeat, delay_ms)
    return _result(outcome, f"press {button} x{repeat} on {where}", "")


@mcp.tool(title="Send a named command", annotations=_ACT)
async def send_command(
    command: Annotated[str, Field(description="A label from list_commands, e.g. 'Netflix' or 'Input HDMI 2'.")],
    target: Target = None,
    repeat: Repeat = 1,
    delay_ms: DelayMs = None,
) -> ActionResult:
    """Send a named command: an activity macro or favorite, or a device command. Names come from list_commands."""
    outcome, label, where = await client().send_command(command, target, repeat, delay_ms)
    return _result(outcome, f"send {label} x{repeat} via {where}", "")


@mcp.tool(title="Find the remote", annotations=_ACT)
async def find_remote() -> ActionResult:
    """Make the physical remote beep so it can be found. Needs sofabaton-x-server (any model)."""
    return _result(await client().find_remote(), "make the remote beep", "")


@mcp.tool(title="Get recent button presses", annotations=_READ)
async def get_recent_presses(
    after_seq: Annotated[
        int | None, Field(ge=0, description="Only presses newer than this seq (from a previous call's last_seq).")
    ] = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> PressPage:
    """Recent presses of remote keys bound to a Wifi Device on the hub (newest first, or oldest first with
    after_seq). Lets a button on the remote ask for something. Comes from sofabaton-x-server's log (any model),
    or on an X2 over MQTT. If instance_id changes, the log restarted and older seqs are gone.
    """
    return await client().presses(after_seq, limit)
