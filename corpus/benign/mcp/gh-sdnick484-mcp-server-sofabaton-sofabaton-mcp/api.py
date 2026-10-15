"""Transport layer: a thin, typed client for sofabaton-x-server's REST API.

No MCP concepts live here (same split as mcp-server-onkyo's transport layer).
Responses are TypedDicts copied from the server's OpenAPI document
(``GET /api/v1/openapi.json``), trimmed to the fields we use.

Every request passes through ``_request``, which only lets through GETs and a
short list of *control* POSTs. sofabaton-x-server can also edit, delete, erase
and restore the hub; those routes need a token we never hold, and this
allow-list is a second, local wall in front of them.
"""

from __future__ import annotations

import re
from typing import Any, Literal, NotRequired, cast

import httpx
from mcp.server.mcpserver.exceptions import ToolError
from typing_extensions import TypedDict

API = "/api/v1"

# The only non-GET calls this client can make (method, path pattern).
_CONTROL_POSTS = (
    re.compile(r"/hubs/[^/]+/activities/\d+/(start|stop)"),
    re.compile(r"/hubs/[^/]+/send"),
    re.compile(r"/hubs/[^/]+/find-remote"),
)


class SofabatonError(ToolError):
    """A problem the model (and user) can act on. Only ToolError text reaches the model."""


# --- response shapes (from the server's OpenAPI schemas) ------------------------
HubMode = Literal["disconnected", "observe", "control"]


class RunningActivity(TypedDict):
    activity_id: int
    name: str | None


class HubStatus(TypedDict):
    hub_connected: bool
    app_connected: bool
    controllable: bool
    mode: HubMode
    hub_version: str | None
    running_activity: RunningActivity | None


class HubStatusView(TypedDict):
    hub_id: str
    enabled: bool
    status: HubStatus | None


class HubConfig(TypedDict):
    host: str
    name: NotRequired[str | None]  # optional in the schema: may be absent, so read it with .get()


class HubView(TypedDict):
    hub_id: str
    enabled: bool
    config: HubConfig
    hub_name: NotRequired[str | None]  # optional in the schema


class HubInfo(TypedDict):
    known: bool
    model: str | None
    name: str | None
    mac: str | None
    firmware_version: int | None
    firmware_outdated: bool


class Activity(TypedDict):
    activity_id: int
    name: str
    active: bool
    needs_confirm: bool


class Device(TypedDict):
    device_id: int
    name: str
    brand: str | None
    device_class: str | None
    power_state: int | None


class Command(TypedDict):
    command_id: int
    label: str


class Macro(TypedDict):
    command_id: int
    label: str | None


class Favorite(TypedDict):
    device_id: int
    command_id: int
    label: str | None


class Accepted(TypedDict):
    accepted: bool
    mode: str


class Press(TypedDict):
    seq: int
    device_id: int
    command_id: int | None
    label: str | None
    press_type: str
    transport: str  # "http" or "mqtt"
    received_at: str


class PressPage(TypedDict):
    instance_id: str
    last_seq: int
    expired: bool
    presses: list[Press]


class ServerAPI:
    """One sofabaton-x-server. Stateless apart from the HTTP connection pool."""

    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None, timeout: float = 10.0) -> None:
        self.base_url = base_url
        # A tool call should fail with a message, not hang the model's turn.
        self._http = httpx.AsyncClient(base_url=base_url + API, transport=transport, timeout=timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: Literal["GET", "POST"], path: str, **kw: Any) -> Any:
        if method != "GET" and not any(p.fullmatch(path) for p in _CONTROL_POSTS):
            # A programming error, not something the model did: tool code
            # tried a route outside the control allow-list.
            raise RuntimeError(f"refusing {method} {path}: not a control route")
        try:
            resp = await self._http.request(method, path, **kw)
        except httpx.TimeoutException as exc:
            raise SofabatonError(f"sofabaton-x-server at {self.base_url} didn't answer in time.") from exc
        except httpx.TransportError as exc:
            raise SofabatonError(
                f"Can't reach sofabaton-x-server at {self.base_url}. Is it running? (Set SOFABATON_URL if it "
                "lives elsewhere.)"
            ) from exc
        if resp.status_code >= 400:
            raise SofabatonError(_problem_text(resp))
        return resp.json() if resp.content else None

    # --- reads -------------------------------------------------------------
    async def version(self) -> str:
        """The server's version, from its OpenAPI document."""
        doc = await self._request("GET", "/openapi.json")
        return str((doc or {}).get("info", {}).get("version", "unknown"))

    async def auth_claimed(self) -> bool:
        """Whether an admin account exists. Unclaimed, the server lets anyone on the LAN write."""
        return bool((await self._request("GET", "/auth") or {}).get("claimed"))

    async def hubs(self) -> list[HubView]:
        return cast(list[HubView], await self._request("GET", "/hubs"))

    async def status(self, hub: str) -> HubStatusView:
        return cast(HubStatusView, await self._request("GET", f"/hubs/{hub}/status"))

    async def info(self, hub: str) -> HubInfo:
        return cast(HubInfo, await self._request("GET", f"/hubs/{hub}/info"))

    async def activities(self, hub: str) -> list[Activity]:
        return cast(list[Activity], await self._request("GET", f"/hubs/{hub}/activities"))

    async def devices(self, hub: str) -> list[Device]:
        return cast(list[Device], await self._request("GET", f"/hubs/{hub}/devices"))

    async def commands(self, hub: str, device_id: int) -> list[Command]:
        return cast(list[Command], await self._request("GET", f"/hubs/{hub}/devices/{device_id}/commands"))

    async def macros(self, hub: str, activity_id: int) -> list[Macro]:
        return cast(list[Macro], await self._request("GET", f"/hubs/{hub}/activities/{activity_id}/macros"))

    async def favorites(self, hub: str, activity_id: int) -> list[Favorite]:
        return cast(list[Favorite], await self._request("GET", f"/hubs/{hub}/activities/{activity_id}/favorites"))

    async def running_activity(self, hub: str) -> RunningActivity | None:
        return cast(RunningActivity | None, await self._request("GET", f"/hubs/{hub}/activity"))

    async def presses(self, hub: str, after: int | None, limit: int) -> PressPage:
        params: dict[str, Any] = {"limit": limit}
        if after is not None:
            params["after"] = after
        return cast(PressPage, await self._request("GET", f"/hubs/{hub}/presses", params=params))

    # --- control (the only POSTs allowed) ------------------------------------
    async def start_activity(self, hub: str, activity_id: int) -> Accepted:
        return cast(Accepted, await self._request("POST", f"/hubs/{hub}/activities/{activity_id}/start"))

    async def stop_activity(self, hub: str, activity_id: int) -> Accepted:
        return cast(Accepted, await self._request("POST", f"/hubs/{hub}/activities/{activity_id}/stop"))

    async def send(self, hub: str, entity_id: int, command_id: int) -> Accepted:
        body = {"entity_id": entity_id, "command_id": command_id}
        return cast(Accepted, await self._request("POST", f"/hubs/{hub}/send", json=body))

    async def find_remote(self, hub: str) -> Accepted:
        return cast(Accepted, await self._request("POST", f"/hubs/{hub}/find-remote"))


def _problem_text(resp: httpx.Response) -> str:
    """Turn the server's RFC 9457 problem body into one actionable sentence."""
    try:
        body = resp.json()
    except ValueError:
        body = {}
    detail = body.get("detail") or body.get("title") or resp.reason_phrase
    if body.get("mode") == "observe":
        return (
            f"{detail} The Sofabaton app is connected through the proxy, which puts the hub in observe "
            "mode; close the app on every phone and tablet."
        )
    if body.get("mode") == "disconnected":
        return f"{detail} The server has no session with the hub right now; check that the hub is powered and online."
    return f"sofabaton-x-server refused the request ({resp.status_code}): {detail}"
