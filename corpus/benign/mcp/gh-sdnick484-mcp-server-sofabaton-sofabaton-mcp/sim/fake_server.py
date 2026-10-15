"""A fake sofabaton-x-server: the REST routes this MCP server uses, as a Starlette app.

One implementation, two harnesses: tests talk to it in-process through
httpx's ASGI transport (``FakeServer.transport``), and `simulate` serves it
with uvicorn on a real port. Behaviors mirror what the real server 0.2.4 was
seen doing with no hub attached (the 409/503 problem bodies) plus its
OpenAPI document (tests/fixtures/*.openapi.json, checked by
test_openapi_contract.py).

Knobs (attributes):
  mode            "control" | "observe" | "disconnected" (ASSUMPTION S-REST-MODES)
  hub_connected   False: catalog reads answer 503
  settle_reads    how many GET /activity reads a start/stop takes to show (a macro
                  still running); None = never shows (a stuck macro)
  unreachable     the transport refuses connections (tests only)
  running         set to put the hub on an activity without telling anyone

The hub itself is a FakeHubState, shared with the fake X2 MQTT side, so a
start through REST is published on MQTT and vice versa.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from .hub_state import Executed, FakeHubState, load_state

API = "/api/v1"


class FakeServer:
    def __init__(self, state: FakeHubState | None = None, hub_id: str = "a1b2c3", host: str = "192.0.2.40") -> None:
        self.state = state or load_state()
        self.hub_id = hub_id
        self.hubs: list[dict[str, Any]] = [
            {
                "hub_id": hub_id,
                "enabled": True,
                "config": {"host": host, "port": 8102, "name": "Living Room", "proxy_enabled": True},
                "added_at": "2026-10-01T00:00:00Z",
                "last_seen": "2026-10-07T00:00:00Z",
                "status": None,
                "hub_name": self.state.name,
            }
        ]
        self.mode = "control"
        self.hub_connected = True
        self.settle_reads: int | None = 1
        self._pending: tuple[int | None, int] | None = None
        self.presses: list[dict[str, Any]] = []
        self.posts: list[tuple[str, Any]] = []
        self.requests: list[tuple[str, str]] = []
        self.unreachable = False
        self.claimed = True  # an admin account exists (False: anyone on the LAN may write)
        self.app = Starlette(routes=[Route(API + "/{path:path}", self._route, methods=["GET", "POST"])])

    # --- the hub's running activity lives in the shared state ---------------------------
    @property
    def running(self) -> int | None:
        return self.state.running

    @running.setter
    def running(self, value: int | None) -> None:
        self.state.running = value  # silently: tests use this to set the scene

    # --- harness ----------------------------------------------------------------------------
    @property
    def transport(self) -> httpx.AsyncBaseTransport:
        return _Transport(self)

    def sends(self) -> list[tuple[int, int]]:
        return [(b["entity_id"], b["command_id"]) for p, b in self.posts if p.endswith("/send")]

    def problem(self, status: int, title: str, detail: str | None = None, mode: str | None = None) -> Response:
        body = {"type": title, "title": title, "status": status, "detail": detail, "hub_id": self.hub_id, "mode": mode}
        return JSONResponse(body, status_code=status)

    # --- routes -------------------------------------------------------------------------------
    async def _route(self, request: Request) -> Response:
        path = "/" + request.path_params["path"]
        self.requests.append((request.method, path))
        if request.method == "POST":
            raw = await request.body()
            body = json.loads(raw) if raw else None
            self.posts.append((path, body))
            return self._post(path, body)
        return self._get(path, dict(request.query_params))

    def _running_view(self) -> dict[str, Any] | None:
        if self._pending is not None:
            target, reads = self._pending
            if reads <= 0:
                self._pending = None
                if target != self.state.running:
                    self.state.running = target
            else:
                self._pending = (target, reads - 1)
        a = self.state.activity(self.state.running) if self.state.running is not None else None
        return {"activity_id": a.activity_id, "name": a.name} if a else None

    def _get(self, path: str, params: dict[str, str]) -> Response:
        st = self.state
        if path == "/openapi.json":
            return JSONResponse({"openapi": "3.1.0", "info": {"title": "sofabaton-x-server", "version": "0.2.4-fake"}})
        if path == "/hubs":
            return JSONResponse(self.hubs)
        if path == "/auth":
            return JSONResponse({"claimed": self.claimed, "signed_in": False})
        prefix = f"/hubs/{self.hub_id}"
        if not path.startswith(prefix):
            return self.problem(404, "hub_not_found")
        sub = path.removeprefix(prefix)
        if sub == "/status":
            a = st.activity(st.running) if st.running is not None else None
            status = {
                "hub_connected": self.hub_connected,
                "app_connected": self.mode == "observe",
                "controllable": self.mode == "control",
                "mode": self.mode,
                "hub_version": st.model,
                "proxy_enabled": True,
                "running_activity": {"activity_id": a.activity_id, "name": a.name} if a else None,
                "activities_cached": len(st.activities),
                "devices_cached": len(st.devices),
                "catalog_ready": True,
                "firmware_version": 300,
                "firmware_min_supported": 200,
                "firmware_unsupported": False,
                "firmware_outdated": False,
            }
            return JSONResponse({"hub_id": self.hub_id, "enabled": True, "status": status})
        if not self.hub_connected:
            # Seen from the real server 0.2.4 with the hub unreachable.
            return self.problem(503, "hub_not_connected", "cannot fetch: the hub is not connected yet", "disconnected")
        if sub == "/info":
            return JSONResponse(
                {
                    "known": True,
                    "model": st.model,
                    "name": st.name,
                    "mac": ":".join(st.mac[i : i + 2] for i in range(0, 12, 2)),
                    "firmware_version": 300,
                    "production_batch": "B1",
                    "firmware_min_supported": 200,
                    "firmware_min_recommended": 250,
                    "firmware_unsupported": False,
                    "firmware_outdated": False,
                }
            )
        if sub == "/activities":
            return JSONResponse(
                [
                    {
                        "activity_id": a.activity_id,
                        "name": a.name,
                        "active": a.activity_id == st.running,
                        "needs_confirm": False,
                        "sort": i,
                    }
                    for i, a in enumerate(st.activities)
                ]
            )
        if sub == "/devices":
            return JSONResponse(
                [
                    {
                        "device_id": d.device_id,
                        "name": d.name,
                        "brand": d.brand,
                        "device_class": d.device_class,
                        "device_class_code": 3,
                        "power_state": 0,
                        "idle_behavior": 0,
                        "sort": d.device_id,
                    }
                    for d in st.devices
                ]
            )
        if sub == "/activity":
            return JSONResponse(self._running_view())
        if sub == "/presses":
            after = int(params["after"]) if "after" in params else None
            rows = [p for p in self.presses if after is None or p["seq"] > after]
            return JSONResponse(
                {"instance_id": "inst1", "last_seq": len(self.presses), "expired": False, "presses": rows}
            )
        if m := re.fullmatch(r"/devices/(\d+)/commands", sub):
            d = st.device(int(m[1]))
            return JSONResponse([{"command_id": c, "label": label} for c, label in (d.commands if d else [])])
        if m := re.fullmatch(r"/activities/(\d+)/macros", sub):
            a = st.activity(int(m[1]))
            return JSONResponse([{"command_id": c, "label": label} for c, label in (a.macros if a else [])])
        if m := re.fullmatch(r"/activities/(\d+)/favorites", sub):
            a = st.activity(int(m[1]))
            rows = [{"device_id": d, "command_id": c, "label": label} for d, c, label in (a.favorites if a else [])]
            return JSONResponse(rows)
        return self.problem(404, "not_found")

    def _post(self, path: str, body: Any) -> Response:
        sub = path.removeprefix(f"/hubs/{self.hub_id}")
        st = self.state
        # The real server (0.2.4, routes_hub_data.py) first checks that the
        # entity exists by reading the catalog: that read is a 503 with no hub
        # session, and a 404 for an unknown id. find-remote skips the check.
        checked = re.fullmatch(r"/activities/(\d+)/(start|stop)", sub) or sub == "/send"
        if checked and not self.hub_connected:
            return self.problem(503, "hub_not_connected", "Hub is not connected", "disconnected")
        if sub == "/send" or (checked and sub != "/send"):
            eid = int(body["entity_id"]) if sub == "/send" else int(checked[1])  # type: ignore[index]
            known = {a.activity_id for a in st.activities} | (
                {d.device_id for d in st.devices} if sub == "/send" else set()
            )
            if eid not in known:
                return self.problem(404, "entity_not_found", f"no entity {eid}", self.mode)
        if self.mode != "control":
            # What the real server does when the proxy doesn't own the hub (seen on 0.2.4).
            return self.problem(409, "send_refused", "the proxy does not own the hub right now", self.mode)
        if m := re.fullmatch(r"/activities/(\d+)/(start|stop)", sub):
            aid = int(m[1])
            st.executed.append(Executed("rest", m[2], aid))
            target = aid if m[2] == "start" else None
            # The hub announces the change on MQTT early in its power macro, before
            # the REST state settles (sofabaton-x docs; ASSUMPTION S-MQTT-STATE).
            before = st.running
            st.set_running(target)
            st.running = before  # the REST view lags behind...
            # ...until settle_reads reads of GET /activity later (None: never, a stuck macro).
            self._pending = (target, self.settle_reads if self.settle_reads is not None else 10**9)
        elif sub == "/send":
            entity, command = int(body["entity_id"]), int(body["command_id"])
            st.executed.append(Executed("rest", "send", entity, command))
        elif sub == "/find-remote":
            st.executed.append(Executed("rest", "find_remote", 0))
        else:
            return self.problem(404, "not_found")
        return JSONResponse({"accepted": True, "mode": self.mode})


class _Transport(httpx.AsyncBaseTransport):
    """httpx -> the ASGI app, plus a switch to refuse connections like a server that's down."""

    def __init__(self, fake: FakeServer) -> None:
        self.fake = fake
        self._asgi = httpx.ASGITransport(app=fake.app)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self.fake.unreachable:
            raise httpx.ConnectError("connection refused", request=request)
        return await self._asgi.handle_async_request(request)
