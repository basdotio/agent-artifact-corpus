"""Domain layer: one hub, reached through sofabaton-x-server, MQTT (X2 only), or both.

Which path a call takes:
  reads    the server when it has a session with the hub (any mode: in observe
           mode it serves its cache); otherwise MQTT.
  control  the server when it is in control mode; otherwise MQTT (an X2 with
           MQTT set up keeps working while the Sofabaton app holds the proxy);
           otherwise an error that says why and what would fix it.

Names in, ids out: the model says "Watch Shield"; each path resolves names
against *its own* catalog and sends ids from that catalog. Ids never cross
from one path to the other, because nothing says the X2's MQTT ids match the
server's (ASSUMPTION S-MQTT-IDS). The catalog is also the allow-list.

A 200 proves nothing. The server's "accepted" means the hub took the frame,
so starts and stops are confirmed: by polling the server's view, or by the
X2's own MQTT announcement, with a list re-read as the fallback.

Capabilities (reported by get_status, so the model knows what this hub can do):
  activities, buttons, commands   list/start/stop, hard buttons, named commands
  find_remote, hub_info           need sofabaton-x-server
  presses                         Wifi-Device key presses (server, or MQTT on an X2)
  live_activity_state             X2 + MQTT: changes pushed as they happen
  control_while_app_open          X2 + MQTT: commands work while the app holds the proxy
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, cast

from typing_extensions import TypedDict

from . import protocol as p
from .api import HubMode, HubStatus, PressPage, RunningActivity, ServerAPI, SofabatonError
from .config import ALLOWED_BUTTONS, BUTTON_CODES, Settings
from .limits import (
    ACTIVITY_CAPACITY,
    ACTIVITY_RATE,
    MAX_DELAY_MS,
    MAX_REPEAT,
    MIN_DELAY_MS,
    PRESS_CAPACITY,
    PRESS_RATE,
    TokenBucket,
)
from .mqtt import ClientFactory, MqttHub
from .tasks import stop_task

log = logging.getLogger(__name__)

Path = Literal["server", "mqtt"]
Model = Literal["X1", "X1S", "X2"]
MQTT_MODELS = ("X2",)  # ASSUMPTION S-X1-NO-MQTT


class ServerState(TypedDict):
    url: str
    hub_id: str | None
    reachable: bool
    hub_connected: bool
    mode: HubMode | None
    app_connected: bool
    error: str | None


class MqttState(TypedDict):
    broker: str
    connected: bool
    login_rejected: bool
    error: str | None


class Status(TypedDict):
    hub_name: str | None
    model: Model | None  # None until the hub has been reached
    via: Path | None  # how a command would go right now; None: it can't
    running_activity: str | None
    transition: str | None  # non-null while an X2's power macro may still be running (MQTT path)
    capabilities: list[str]
    limitations: list[str]  # what this hub can't do here, and what would enable it
    firmware_outdated: bool | None
    server: ServerState | None
    mqtt: MqttState | None


@dataclass(frozen=True)
class Outcome:
    changed: bool
    via: Path
    sent: list[str] = field(default_factory=list)  # what went on the wire (or would, in dry-run)
    dry_run: bool = False
    note: str = ""


@dataclass(frozen=True)
class CommandOption:
    label: str
    kind: Literal["macro", "favorite", "device"]
    entity_id: int  # the activity (macro) or device (favorite, device command), in the path's id space
    key_id: int
    via: str  # "activity" or the name of the device that gets it


@dataclass(frozen=True)
class _ServerView:
    reachable: bool
    status: HubStatus | None
    error: str | None


def _norm(name: str) -> str:
    """Case-, space- and punctuation-insensitive matching key ("Watch-Shield" == "watch shield")."""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _names(items: list[str]) -> str:
    return ", ".join(items) if items else "(none)"


class SofabatonClient:
    # The hub runs an activity's power macro (devices on, inputs set, delays)
    # before reporting it running.
    activity_timeout = 30.0  # how long a power macro may take before we say so. ASSUMPTION S-REST-START
    poll_interval = 0.5
    repeat_gap = 0.3  # default pause between repeated presses
    identity_retry = 30.0  # seconds between attempts to learn model/MAC from the server
    # A client may call a tool the moment it launches us (MCP Inspector's CLI mode, get_status at startup),
    # before the broker connection is up. The first call waits this long for it, once; later calls don't
    # wait, so a broker that goes away is reported at once.
    mqtt_startup_grace = 3.0

    def __init__(self, settings: Settings, api: ServerAPI | None, mqtt_factory: ClientFactory | None = None) -> None:
        self.settings = settings
        self.api = api
        self._mqtt_factory = mqtt_factory
        self.mqtt: MqttHub | None = None
        self.mqtt_blocked: str | None = None  # why MQTT isn't being used, when it's configured
        self.model: Model | None = None if api is not None else ("X2" if settings.mqtt else None)
        self.hub_name: str | None = None
        self._hub_id: str | None = None
        self._identity_task: asyncio.Task[None] | None = None
        self._mqtt_grace_used = False
        self.press_bucket = TokenBucket(PRESS_CAPACITY, PRESS_RATE)
        self.activity_bucket = TokenBucket(ACTIVITY_CAPACITY, ACTIVITY_RATE)

    # --- lifecycle --------------------------------------------------------------------
    async def start(self) -> None:
        for problem in self.settings.problems:
            log.warning("Config: %s", problem)
        if self.settings.dry_run:
            log.warning("DRY RUN: the hub is read, but nothing that changes anything is sent.")
        m = self.settings.mqtt
        if m is None:
            return
        if m.mac:
            await self._start_mqtt(m.mac)
        if self.api is not None:
            # Learn the model (and the MAC, if not configured) from the server, in
            # the background: the hub may be off right now.
            self._identity_task = asyncio.create_task(self._learn_identity(), name="sofabaton-identity")

    async def stop(self) -> None:
        await stop_task(self._identity_task, 5.0, "Learning the hub's identity")
        if self.mqtt is not None:
            await self.mqtt.stop()
        if self.api is not None:
            await self.api.aclose()

    async def _start_mqtt(self, mac: str) -> None:
        assert self.settings.mqtt is not None
        self.mqtt = MqttHub(self.settings.mqtt, mac, self._mqtt_factory)
        await self.mqtt.start()

    async def _learn_identity(self) -> None:
        assert self.api is not None
        while True:
            try:
                info = await self.api.info(await self.hub_id())
            except SofabatonError as exc:
                log.debug("hub identity not available yet: %s", exc)
                await asyncio.sleep(self.identity_retry)
                continue
            if not info.get("known"):
                await asyncio.sleep(self.identity_retry)
                continue
            model = info.get("model")
            if model in ("X1", "X1S", "X2"):
                self.model = model  # type: ignore[assignment]
            if self.model is not None and self.model not in MQTT_MODELS:
                self.mqtt_blocked = (
                    f"MQTT is configured, but this hub is an {self.model}: the MQTT features need an X2. "
                    "Everything else works through sofabaton-x-server."
                )
                if self.mqtt is not None:
                    await self.mqtt.stop()
                    self.mqtt = None
                return
            if self.mqtt is None:
                mac = p.normalize_mac(str(info.get("mac") or ""))
                if mac is None:
                    self.mqtt_blocked = "sofabaton-x-server didn't report the X2's MAC; set SOFABATON_MQTT_MAC."
                    return
                await self._start_mqtt(mac)
            return

    # --- which hub on the server ------------------------------------------------------
    async def hub_id(self) -> str:
        """Resolve SOFABATON_HUB (id or name) once; with one hub, just use it."""
        if self._hub_id is not None:
            return self._hub_id
        assert self.api is not None
        hubs = await self.api.hubs()
        wanted = self.settings.hub
        if wanted:
            key = _norm(wanted)
            match = [
                h
                for h in hubs
                if h["hub_id"] == wanted
                or key in (_norm(h.get("hub_name") or ""), _norm(h["config"].get("name") or ""))
            ]
        else:
            match = hubs
        if len(match) != 1:
            listed = _names([f"{h['hub_id']} ({h.get('hub_name') or h['config']['host']})" for h in hubs])
            if not hubs:
                raise SofabatonError("sofabaton-x-server has no hubs yet; add one in its control panel (/ui/).")
            if wanted:
                raise SofabatonError(f"No hub matches SOFABATON_HUB={wanted!r}. Hubs: {listed}")
            raise SofabatonError(f"sofabaton-x-server manages several hubs; set SOFABATON_HUB to one of: {listed}")
        self._hub_id = match[0]["hub_id"]
        self.hub_name = match[0].get("hub_name") or match[0]["config"].get("name")
        return self._hub_id

    # --- path selection ---------------------------------------------------------------------
    async def _server_view(self) -> _ServerView | None:
        if self.api is None:
            return None
        try:
            view = await self.api.status(await self.hub_id())
        except SofabatonError as exc:
            return _ServerView(False, None, str(exc))
        st = view["status"]
        # hub_version is only meaningful once the server has talked to the hub.
        version = st.get("hub_version") if st else None
        if st and st["hub_connected"] and version in ("X1", "X1S", "X2"):
            self.model = cast(Model, version)
        return _ServerView(True, st, None)

    async def _mqtt_startup(self) -> None:
        """On the first call only: give a just-started MQTT connection a moment to come up."""
        if self._mqtt_grace_used:
            return
        self._mqtt_grace_used = True
        m = self.mqtt
        if m is None or self.mqtt_blocked:
            return
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.mqtt_startup_grace
        while not (m.connected or m.auth_failed) and loop.time() < deadline:
            await asyncio.sleep(0.05)

    def _mqtt_ok(self) -> bool:
        return self.mqtt is not None and self.mqtt.connected and self.mqtt_blocked is None

    def _mqtt_reason(self) -> str:
        """Why MQTT can't help right now, or "" if it isn't configured at all."""
        if self.settings.mqtt is None:
            return ""
        if self.mqtt_blocked:
            return self.mqtt_blocked
        if self.mqtt is None:
            return "MQTT is waiting to learn the X2's MAC from sofabaton-x-server (or set SOFABATON_MQTT_MAC)."
        if self.mqtt.auth_failed:
            return f"the MQTT broker at {self.mqtt.broker} rejected the login (check SOFABATON_MQTT_URL)."
        return f"not connected to the MQTT broker at {self.mqtt.broker} ({self.mqtt.last_error or 'connecting'})."

    def _x2_hint(self) -> str:
        if self.settings.mqtt is None and self.model == "X2":
            return " On this X2, setting up MQTT (SOFABATON_MQTT_URL) would keep it controllable even then."
        if reason := self._mqtt_reason():
            return f" MQTT can't take over: {reason}"
        return ""

    def _no_path(self, sv: _ServerView | None, control: bool) -> SofabatonError:
        if sv is None:
            return SofabatonError(f"Can't reach the X2: {self._mqtt_reason()}")
        if not sv.reachable:
            return SofabatonError(f"{sv.error}{self._x2_hint()}")
        st = sv.status
        if control and st is not None and st["mode"] == "observe":
            return SofabatonError(
                "The Sofabaton app is connected through sofabaton-x-server's proxy (observe mode), so commands are "
                f"refused; close the app on every phone and tablet.{self._x2_hint()}"
            )
        return SofabatonError(
            "sofabaton-x-server has no session with the hub right now; check that it's powered and online."
            + self._x2_hint()
        )

    async def _read_path(self) -> Path:
        await self._mqtt_startup()
        sv = await self._server_view()
        if sv is not None and sv.reachable and sv.status is not None and sv.status["hub_connected"]:
            return "server"
        if self._mqtt_ok():
            return "mqtt"
        raise self._no_path(sv, control=False)

    async def _control_path(self) -> Path:
        await self._mqtt_startup()
        sv = await self._server_view()
        if sv is not None and sv.reachable and sv.status is not None and sv.status["mode"] == "control":
            return "server"
        if self._mqtt_ok():
            return "mqtt"
        raise self._no_path(sv, control=True)

    def _mqtt_hub(self) -> MqttHub:
        assert self.mqtt is not None
        return self.mqtt

    # --- status -------------------------------------------------------------------------------
    def _capabilities(self, sv: _ServerView | None) -> tuple[list[str], list[str]]:
        """What works on this hub right now, and what doesn't (with what would fix it).

        Capability names: catalog (list activities/devices/commands), activities (start/power off), buttons,
        commands, presses, find_remote, hub_info (model/firmware), live_activity_state and
        control_while_app_open (both X2 over MQTT).
        """
        server_ok = sv is not None and sv.reachable and sv.status is not None and sv.status["hub_connected"]
        observe = server_ok and sv is not None and sv.status is not None and sv.status["mode"] == "observe"
        server_control = server_ok and not observe
        mqtt_ok = self._mqtt_ok()
        caps: list[str] = []
        limits: list[str] = []
        if server_ok or mqtt_ok:
            caps += ["catalog"]
        if server_control or mqtt_ok:
            caps += ["activities", "buttons", "commands"]
        if server_ok or mqtt_ok:
            caps += ["presses"]
        if server_control:
            caps += ["find_remote"]
        if server_ok:
            caps += ["hub_info"]
        if mqtt_ok:
            caps += ["live_activity_state", "control_while_app_open"]
        if self.model in ("X1", "X1S"):
            limits.append(
                f"This is an {self.model}: live activity state, control while the Sofabaton app is open, and "
                "MQTT presses need an X2."
            )
        elif self.settings.mqtt is None and self.model == "X2":
            limits.append(
                "MQTT isn't set up: with SOFABATON_MQTT_URL this X2 would also get live activity state and stay "
                "controllable while the Sofabaton app is open."
            )
        elif (reason := self._mqtt_reason()) and not mqtt_ok:
            limits.append(f"MQTT unavailable: {reason}")
        if self.api is None:
            limits.append(
                "No sofabaton-x-server: find_remote and firmware details are unavailable (no MQTT topic for them)."
            )
        elif not server_ok:
            limits.append(f"sofabaton-x-server: {sv.error if sv and sv.error else 'no session with the hub'}")
        if observe and mqtt_ok:
            limits.append(
                "The Sofabaton app holds sofabaton-x-server's proxy (observe mode): commands go over MQTT meanwhile, "
                "and find_remote waits until the app is closed."
            )
        elif observe:
            limits.append(
                "The Sofabaton app holds the proxy (observe mode): reads work, but commands are refused until it's "
                "closed on every phone and tablet."
            )
        return caps, limits

    async def status(self) -> Status:
        await self._mqtt_startup()
        sv = await self._server_view()
        caps, limits = self._capabilities(sv)
        st = sv.status if sv else None
        server: ServerState | None = None
        if self.api is not None:
            server = {
                "url": self.settings.url or "",
                "hub_id": self._hub_id,
                "reachable": bool(sv and sv.reachable),
                "hub_connected": bool(st and st["hub_connected"]),
                "mode": st["mode"] if st else None,
                "app_connected": bool(st and st["app_connected"]),
                "error": sv.error if sv else None,
            }
        mqtt: MqttState | None = None
        if self.settings.mqtt is not None:
            m = self.mqtt
            mqtt = {
                "broker": m.broker if m else f"{self.settings.mqtt.host}:{self.settings.mqtt.port}",
                "connected": bool(m and m.connected),
                "login_rejected": bool(m and m.auth_failed),
                "error": self.mqtt_blocked or (m.last_error if m else None),
            }
        running: str | None = None
        via: Path | None = None
        outdated: bool | None = None
        try:
            via = await self._control_path()
        except SofabatonError:
            via = None
        try:
            got = await self._running(await self._read_path())
            running = got[1] if got else None
        except SofabatonError:
            pass
        if st and st["hub_connected"] and self.api is not None:
            try:
                info = await self.api.info(await self.hub_id())
                outdated = info["firmware_outdated"]
                self.hub_name = info["name"] or self.hub_name
            except SofabatonError as exc:  # identity is nice-to-have; don't fail status over it
                log.info("hub info unavailable: %s", exc)
        transition = None
        if self._mqtt_ok() and (left := self._mqtt_hub().settling_for(self.settings.settle_s)) > 0 and via == "mqtt":
            transition = f"power macro may still be running (presses wait {left:.0f}s more)"
        name = self.hub_name or (f"X2 {self.mqtt.mac[-4:]}" if self.mqtt else None)
        return {
            "hub_name": name,
            "model": self.model,
            "via": via,
            "running_activity": running,
            "transition": transition,
            "capabilities": caps,
            "limitations": limits,
            "firmware_outdated": outdated,
            "server": server,
            "mqtt": mqtt,
        }

    # --- catalog, per path ---------------------------------------------------------------------
    async def _activities(self, path: Path) -> list[tuple[int, str, bool]]:
        if path == "server":
            assert self.api is not None
            return [(a["activity_id"], a["name"], a["active"]) for a in await self.api.activities(await self.hub_id())]
        return await self._mqtt_hub().activities()

    async def _devices(self, path: Path) -> list[tuple[int, str, str | None, str | None]]:
        """(id, name, brand, class); MQTT knows only ids and names."""
        if path == "server":
            assert self.api is not None
            return [
                (d["device_id"], d["name"], d["brand"], d["device_class"])
                for d in await self.api.devices(await self.hub_id())
            ]
        return [(i, n, None, None) for i, n in await self._mqtt_hub().devices()]

    async def activities(self) -> list[tuple[str, bool]]:
        return [(name, on) for _, name, on in await self._activities(await self._read_path())]

    async def devices(self) -> list[tuple[str, str | None, str | None]]:
        return [(n, b, c) for _, n, b, c in await self._devices(await self._read_path())]

    async def _running(self, path: Path) -> tuple[int, str] | None:
        if path == "server":
            assert self.api is not None
            ra: RunningActivity | None = await self.api.running_activity(await self.hub_id())
            return (ra["activity_id"], ra["name"] or str(ra["activity_id"])) if ra else None
        on = [(i, n) for i, n, is_on in await self._mqtt_hub().activities() if is_on]
        return on[0] if on else None

    async def _find_activity(self, path: Path, name: str) -> tuple[int, str]:
        acts = await self._activities(path)
        hit = next(((i, n) for i, n, _ in acts if _norm(n) == _norm(name)), None)
        if hit is None:
            raise SofabatonError(f"Unknown activity {name!r}. Activities: {_names([n for _, n, _ in acts])}")
        return hit

    async def _target(self, path: Path, name: str | None) -> tuple[Literal["activity", "device"], int, str]:
        """Resolve an activity or device name (None: the running activity) in this path's id space."""
        if name is None:
            running = await self._running(path)
            if running is None:
                raise SofabatonError("No activity is running. Name a device, or start an activity first.")
            return "activity", running[0], running[1]
        key = _norm(name)
        acts = await self._activities(path)
        if a := next(((i, n) for i, n, _ in acts if _norm(n) == key), None):
            return "activity", a[0], a[1]
        devs = await self._devices(path)
        if d := next(((i, n) for i, n, _, _ in devs if _norm(n) == key), None):
            return "device", d[0], d[1]
        raise SofabatonError(
            f"No activity or device named {name!r}. Activities: {_names([n for _, n, _ in acts])}. "
            f"Devices: {_names([n for _, n, _, _ in devs])}."
        )

    async def _options(self, path: Path, kind: str, entity_id: int) -> list[CommandOption]:
        """Every named command for an activity (macros, favorites) or a device, in this path's ids."""
        if path == "server":
            assert self.api is not None
            hub = await self.hub_id()
            if kind == "device":
                return [
                    CommandOption(c["label"], "device", entity_id, c["command_id"], "device")
                    for c in await self.api.commands(hub, entity_id)
                ]
            names = {i: n for i, n, _, _ in await self._devices(path)}
            out = [
                CommandOption(m["label"], "macro", entity_id, m["command_id"], "activity")
                for m in await self.api.macros(hub, entity_id)
                if m["label"]
            ]
            out += [
                CommandOption(
                    f["label"],
                    "favorite",
                    f["device_id"],
                    f["command_id"],
                    names.get(f["device_id"], str(f["device_id"])),
                )
                for f in await self.api.favorites(hub, entity_id)
                if f["label"]
            ]
            return out
        mq = self._mqtt_hub()
        if kind == "device":
            return [
                CommandOption(label, "device", entity_id, k, "device")
                for k, label in await mq.device_keys(entity_id)
                if label
            ]
        names = {i: n for i, n in await mq.devices()}
        out = [
            CommandOption(label, "macro", entity_id, k, "activity") for k, label in await mq.macros(entity_id) if label
        ]
        out += [
            CommandOption(label, "favorite", d, k, names.get(d, str(d)))
            for d, k, label in await mq.favorites(entity_id)
            if label
        ]
        return out

    async def commands(self, target: str | None) -> tuple[str, list[CommandOption]]:
        path = await self._read_path()
        kind, entity_id, display = await self._target(path, target)
        return f"{kind} {display}", await self._options(path, kind, entity_id)

    # --- control ------------------------------------------------------------------------------------
    def _limit(self, bucket: TokenBucket, n: int, what: str) -> None:
        wait = bucket.take(n)
        if wait:
            when = "more than the limit allows at once" if wait == float("inf") else f"try again in {wait:.0f}s"
            raise SofabatonError(
                f"Rate limit: refusing to {what} ({when}). This guards against runaway loops; if it's deliberate, wait "
                "and retry."
            )

    def _check_settle(self, path: Path) -> None:
        """ASSUMPTION S-MQTT-SETTLE: over MQTT nothing says when a power macro ends, so wait out a window."""
        if path != "mqtt":
            return  # sofabaton-x-server holds commands until the hub reports ready
        left = self._mqtt_hub().settling_for(self.settings.settle_s)
        if left > 0:
            raise SofabatonError(
                f"The X2 just changed activity and its power macro may still be running; a press now could interrupt "
                f"it. Try again in {left:.0f}s (SOFABATON_MQTT_SETTLE_S sets this window)."
            )

    @staticmethod
    def _wire(topic_key: str, payload: object) -> str:
        """How an MQTT publish is described in results: the topic with <MAC>, never the real one."""
        return f"publish {p.topics('<MAC>')[topic_key]} {json.dumps(payload)}"

    async def start_activity(self, name: str) -> tuple[Outcome, str]:
        """Start it and confirm. Returns (outcome, the activity's canonical name)."""
        path = await self._control_path()
        aid, canon = await self._find_activity(path, name)
        running = await self._running(path)
        if running and running[0] == aid:
            return Outcome(False, path), canon
        self._limit(self.activity_bucket, 1, f"start {canon}")
        if path == "server":
            assert self.api is not None
            hub = await self.hub_id()
            sent = [f"POST /api/v1/hubs/{hub}/activities/{aid}/start"]
            if self.settings.dry_run:
                return Outcome(False, path, sent, dry_run=True), canon
            await self.api.start_activity(hub, aid)
            await self._confirm_server(hub, lambda r: r is not None and r["activity_id"] == aid, canon)
            return Outcome(True, path, sent), canon
        payload = p.activity_state(aid, True)
        sent = [self._wire("state_down", payload)]
        if self.settings.dry_run:
            return Outcome(False, path, sent, dry_run=True), canon
        await self._mqtt_hub().publish("state_down", payload)
        await self._confirm_mqtt(lambda cur: cur == aid, canon)
        note = (
            "The X2 announced it early; its power macro may run for a few more seconds "
            f"(presses wait {self.settings.settle_s:.0f}s)."
        )
        return Outcome(True, path, sent, note=note), canon

    async def power_off(self) -> tuple[Outcome, str | None]:
        """Power off the running activity and confirm. (outcome, its name or None if nothing ran)."""
        path = await self._control_path()
        running = await self._running(path)
        if running is None:
            return Outcome(False, path), None
        aid, name = running
        self._limit(self.activity_bucket, 1, f"power off {name}")
        if path == "server":
            assert self.api is not None
            hub = await self.hub_id()
            sent = [f"POST /api/v1/hubs/{hub}/activities/{aid}/stop"]
            if self.settings.dry_run:
                return Outcome(False, path, sent, dry_run=True), name
            await self.api.stop_activity(hub, aid)
            await self._confirm_server(hub, lambda r: r is None or r["activity_id"] != aid, f"power off {name}")
            return Outcome(True, path, sent), name
        payload = p.activity_state(aid, False)
        sent = [self._wire("state_down", payload)]
        if self.settings.dry_run:
            return Outcome(False, path, sent, dry_run=True), name
        await self._mqtt_hub().publish("state_down", payload)
        await self._confirm_mqtt(lambda cur: cur != aid, f"power off {name}")
        return Outcome(True, path, sent), name

    async def _confirm_server(self, hub: str, done: Callable[[RunningActivity | None], bool], what: str) -> None:
        """Poll the server's running activity until done(it); a few looks a second is plenty."""
        assert self.api is not None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.activity_timeout
        while loop.time() < deadline:
            if done(await self.api.running_activity(hub)):
                return
            await asyncio.sleep(self.poll_interval)
        raise SofabatonError(
            f"The hub accepted '{what}' but didn't report it finished within {self.activity_timeout:.0f}s. "
            "It may still be running its macro; check get_status before retrying."
        )

    async def _confirm_mqtt(self, done: Callable[[int | None], bool], what: str) -> None:
        """Wait for the X2's own announcement (activity_control_up); if none comes, ask for the list."""
        mq = self._mqtt_hub()
        if await mq.wait_state(done, self.activity_timeout):
            return
        await mq.activities()  # refreshes mq.current from the hub's list
        if done(mq.current):
            log.warning("No activity_control_up for '%s', but the activity list confirms it (S-MQTT-STATE)", what)
            return
        raise SofabatonError(
            f"The X2 didn't confirm '{what}' over MQTT within {self.activity_timeout:.0f}s. It may still be running "
            "its macro; check get_status before retrying."
        )

    def _gap(self, delay_ms: int | None, repeat: int) -> float:
        if delay_ms is not None and not MIN_DELAY_MS <= delay_ms <= MAX_DELAY_MS:
            raise SofabatonError(f"delay_ms must be {MIN_DELAY_MS}-{MAX_DELAY_MS}.")
        if not 1 <= repeat <= MAX_REPEAT:
            raise SofabatonError(f"repeat must be 1-{MAX_REPEAT}.")
        return self.repeat_gap if delay_ms is None else delay_ms / 1000

    async def _send_repeated(self, send: Callable[[], object], repeat: int, gap: float) -> None:
        for i in range(repeat):
            if i:
                await asyncio.sleep(gap)
            result = send()
            if asyncio.iscoroutine(result):
                await result

    async def press(
        self, button: str, target: str | None, repeat: int = 1, delay_ms: int | None = None
    ) -> tuple[Outcome, str]:
        """Press a hard button. Returns (outcome, 'activity X' / 'device Y')."""
        # Re-check even though the tool schema is an enum: last line of defense.
        if button not in ALLOWED_BUTTONS:
            raise SofabatonError(f"Button {button!r} is not allowed.")
        gap = self._gap(delay_ms, repeat)
        path = await self._control_path()
        kind, eid, display = await self._target(path, target)
        where = f"{kind} {display}"
        code = BUTTON_CODES[button]
        if path == "mqtt" and kind == "device":
            raise SofabatonError(
                "Over MQTT, the X2 takes remote buttons through an activity (activity/<MAC>/keys_control). Name an "
                "activity, or use send_command for this device's own commands."
            )
        self._check_settle(path)
        self._limit(self.press_bucket, repeat, f"press {button} x{repeat}")
        if path == "server":
            assert self.api is not None
            hub = await self.hub_id()
            sent = [f'POST /api/v1/hubs/{hub}/send {{"entity_id": {eid}, "command_id": {code}}}'] * repeat
            if self.settings.dry_run:
                return Outcome(False, path, sent, dry_run=True), where
            api = self.api
            await self._send_repeated(lambda: api.send(hub, eid, code), repeat, gap)
            return Outcome(True, path, sent), where
        payload = p.activity_key(eid, code)
        sent = [self._wire("key_ctl", payload)] * repeat
        if self.settings.dry_run:
            return Outcome(False, path, sent, dry_run=True), where
        mq = self._mqtt_hub()
        await self._send_repeated(lambda: mq.publish("key_ctl", payload), repeat, gap)
        return Outcome(True, path, sent), where

    async def send_command(
        self, label: str, target: str | None, repeat: int = 1, delay_ms: int | None = None
    ) -> tuple[Outcome, str, str]:
        """Send a named macro/favorite/device command. Returns (outcome, canonical label, 'activity X'/'device Y')."""
        gap = self._gap(delay_ms, repeat)
        path = await self._control_path()
        kind, eid, display = await self._target(path, target)
        where = f"{kind} {display}"
        options = await self._options(path, kind, eid)
        opt = next((o for o in options if _norm(o.label) == _norm(label)), None)
        if opt is None:
            raise SofabatonError(f"{where} has no command {label!r}. Use list_commands to see what it accepts.")
        self._check_settle(path)
        self._limit(self.press_bucket, repeat, f"send {opt.label} x{repeat}")
        if path == "server":
            assert self.api is not None
            hub = await self.hub_id()
            # Over REST, a favorite is sent to its device, a macro to its activity.
            sent = [
                f'POST /api/v1/hubs/{hub}/send {{"entity_id": {opt.entity_id}, "command_id": {opt.key_id}}}'
            ] * repeat
            if self.settings.dry_run:
                return Outcome(False, path, sent, dry_run=True), opt.label, where
            api = self.api
            await self._send_repeated(lambda: api.send(hub, opt.entity_id, opt.key_id), repeat, gap)
            return Outcome(True, path, sent), opt.label, where
        key, payload = {
            "macro": ("macro_ctl", p.activity_key(opt.entity_id, opt.key_id)),
            "favorite": ("favorite_ctl", p.favorite_key(opt.entity_id, opt.key_id)),
            "device": ("device_key_ctl", p.device_key(opt.entity_id, opt.key_id)),
        }[opt.kind]
        sent = [self._wire(key, payload)] * repeat
        if self.settings.dry_run:
            return Outcome(False, path, sent, dry_run=True), opt.label, where
        mq = self._mqtt_hub()
        await self._send_repeated(lambda: mq.publish(key, payload), repeat, gap)
        return Outcome(True, path, sent), opt.label, where

    async def find_remote(self) -> Outcome:
        sv = await self._server_view()
        if self.api is None:
            raise SofabatonError(
                "find_remote needs sofabaton-x-server; this X2 is set up for MQTT only, and none of the documented "
                "MQTT topics make the remote beep."
            )
        if sv is None or not sv.reachable or sv.status is None or sv.status["mode"] != "control":
            raise self._no_path(sv, control=True)
        hub = await self.hub_id()
        sent = [f"POST /api/v1/hubs/{hub}/find-remote"]
        if self.settings.dry_run:
            return Outcome(False, "server", sent, dry_run=True)
        await self.api.find_remote(hub)
        return Outcome(True, "server", sent)

    async def presses(self, after: int | None, limit: int) -> PressPage:
        sv = await self._server_view()
        if sv is not None and sv.reachable and self.api is not None:
            return await self.api.presses(await self.hub_id(), after, limit)
        if self._mqtt_ok():
            return self._mqtt_hub().presses(after, limit)
        raise self._no_path(sv, control=False)
