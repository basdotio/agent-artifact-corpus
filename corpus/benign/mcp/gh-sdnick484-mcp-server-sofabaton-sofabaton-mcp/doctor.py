"""`mcp-server-sofabaton doctor`: check each way to the hub, layer by layer, and say what failed.

  config   settings parse (Settings.problems)
  server   (if configured) reachable, version, claimed, hub found, session, mode,
           model/MAC/firmware, catalog readable
  mqtt     (if configured; X2 only) broker login, the X2 answering an activity
           list request on its MAC's topics, live state known
  listen   (--listen N) print every message under activity/#, device/# and +/up
           for N seconds: press keys on the remote and watch what the X2 sends

When the X2 doesn't answer on the UPPERCASE-MAC topics, doctor also tries the
lowercase MAC and reports which one worked: that settles ASSUMPTION
S-MQTT-MAC-CASE on your hub either way.

`--dump DIR` writes what both paths return to DIR/sofabaton.json, with the MAC
and addresses redacted: the server's catalog, and every MQTT message as the
X2 sent it (one reply of each list type). Copy it to tests/fixtures/recorded/
and test_recorded.py replays it through the real parsers.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import platform
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .api import ServerAPI, SofabatonError
from .assumptions import unverified
from .client import SofabatonClient
from .config import Settings
from .logsafe import redact
from .mqtt import ClientFactory, MqttHub
from .protocol import normalize_mac

TESTED_SERVER = "0.2"  # the sofabaton-x-server minor version this was built against


@dataclass
class Check:
    step: str
    ok: bool
    detail: str
    hint: str = ""


@dataclass
class Report:
    versions: dict[str, str]
    config_problems: list[str]
    checks: list[Check] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    heard: list[str] = field(default_factory=list)  # --listen
    unverified_assumptions: list[str] = field(default_factory=list)
    dumped_to: str | None = None

    @property
    def ok(self) -> bool:
        return not self.config_problems and bool(self.checks) and all(c.ok for c in self.checks)


def versions() -> dict[str, str]:
    out = {"python": platform.python_version()}
    for pkg in ("mcp-server-sofabaton", "mcp", "httpx", "aiomqtt"):
        try:
            out[pkg] = version(pkg)
        except PackageNotFoundError:
            out[pkg] = "not installed"
    return out


async def _server_checks(
    settings: Settings, api: ServerAPI, report: Report, dump: dict[str, Any]
) -> tuple[str | None, str | None]:
    """Returns the hub's MAC (uppercase bare hex) and model, as far as the server knows them."""
    c = SofabatonClient(replace(settings, mqtt=None), api)
    try:
        ver = await api.version()
    except SofabatonError as exc:
        report.checks.append(
            Check("server", False, str(exc), "Is sofabaton-x-server running, and is SOFABATON_URL its address?")
        )
        return None, None
    ok_version = ver.startswith(TESTED_SERVER)
    report.checks.append(Check("server", True, f"sofabaton-x-server {ver} at {settings.url}"))
    if not ok_version:
        report.warnings.append(
            f"Built against sofabaton-x-server {TESTED_SERVER}.x; this is {ver}. Run the tests against it."
        )
    with contextlib.suppress(SofabatonError):
        if not await api.auth_claimed():
            report.warnings.append(
                "sofabaton-x-server is unclaimed: anyone on the LAN can edit or erase the hub through it. Set up an "
                "admin account in its control panel (Server settings > Access)."
            )
    try:
        hub = await c.hub_id()
        view = (await api.status(hub))["status"]
    except SofabatonError as exc:
        report.checks.append(Check("hub", False, str(exc)))
        return None, None
    if view is None or not view["hub_connected"]:
        report.checks.append(
            Check(
                "hub",
                False,
                f"hub {hub}: the server has no session with it",
                "Is the hub powered and online? Check the server's control panel.",
            )
        )
        return None, None
    mode = view["mode"]
    report.checks.append(
        Check(
            "hub",
            mode == "control",
            f"hub {hub}: session up, mode {mode}",
            ""
            if mode == "control"
            else "The Sofabaton app is connected through the proxy; close it on every phone and tablet.",
        )
    )
    mac = model = None
    try:
        info = await api.info(hub)
        model = info["model"]
        mac = normalize_mac(str(info.get("mac") or ""))
        report.checks.append(
            Check(
                "identity",
                True,
                f"{info['model']} '{info['name']}', firmware {info['firmware_version']}, MAC {mac or 'unknown'}",
            )
        )
        if info["firmware_outdated"]:
            report.warnings.append(
                "The hub's firmware is older than sofabaton-x-server recommends; update it in the Sofabaton app."
            )
        if info["model"] in ("X1", "X1S") and settings.mqtt is not None:
            report.warnings.append(f"MQTT is configured, but this is an {info['model']}: MQTT features need an X2.")
        acts = await api.activities(hub)
        devs = await api.devices(hub)
        report.checks.append(Check("catalog", bool(acts), f"{len(acts)} activities, {len(devs)} devices over REST"))
        dump["server"] = {"version": ver, "info": info, "activities": acts, "devices": devs}
    except SofabatonError as exc:
        report.checks.append(Check("identity", False, str(exc)))
    return mac, model


async def _mqtt_checks(
    settings: Settings, mac: str, report: Report, dump: dict[str, Any], timeout: float, factory: ClientFactory | None
) -> None:
    assert settings.mqtt is not None

    async def probe(candidate: str) -> tuple[MqttHub, list[tuple[int, str, bool]] | None]:
        hub = MqttHub(settings.mqtt, candidate, factory)  # type: ignore[arg-type]
        hub.reply_timeout = timeout
        hub.raw_log = []
        await hub.start()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while not hub.connected and not hub.auth_failed and loop.time() < deadline:
            await asyncio.sleep(0.05)
        if not hub.connected:
            return hub, None
        try:
            return hub, await hub.activities()
        except SofabatonError:
            return hub, None

    hub, acts = await probe(mac)
    try:
        if not hub.connected:
            why = "login rejected" if hub.auth_failed else (hub.last_error or "no answer")
            report.checks.append(
                Check(
                    "mqtt",
                    False,
                    f"broker {hub.broker}: {why}",
                    "Check SOFABATON_MQTT_URL (host, port, user, password). It must be the broker you entered in the "
                    "Sofabaton app (Me -> Connect to Home Assistant).",
                )
            )
            return
        report.checks.append(Check("mqtt", True, f"broker {hub.broker}: logged in"))
        if acts is None:
            other, other_acts = await probe(mac.lower())
            await other.stop()
            if other_acts is not None:
                report.checks.append(
                    Check(
                        "x2",
                        False,
                        "the X2 answered on the *lowercase*-MAC topics, not uppercase",
                        "ASSUMPTION S-MQTT-MAC-CASE is wrong for this hub: please report this (and the doctor output).",
                    )
                )
                return
            report.checks.append(
                Check(
                    "x2",
                    False,
                    f"no reply to activity/<MAC>/list_request within {timeout:.0f}s",
                    "Is the X2's MQTT link set up to this broker (Sofabaton app: Me -> Connect to Home Assistant)? "
                    "Is the MAC right? Try `doctor --listen 30` and press keys on the remote.",
                )
            )
            return
        on = [n for _, n, is_on in acts if is_on]
        report.checks.append(
            Check("x2", True, f"answered over MQTT: {len(acts)} activities, running: {on[0] if on else 'nothing'}")
        )
        devs = await hub.devices()
        # One of each list request, so a --dump holds every reply shape the X2 sends (S-MQTT-LISTS).
        if acts:
            first_activity = acts[0][0]
            for what, call in (
                ("keys_request", hub.activity_keys),
                ("macro_keys_request", hub.macros),
                ("favorites_keys_request", hub.favorites),
            ):
                try:
                    await call(first_activity)
                except SofabatonError:
                    report.warnings.append(f"The X2 didn't answer activity/<MAC>/{what} (S-MQTT-LISTS).")
        if devs:
            try:
                await hub.device_keys(devs[0][0])
            except SofabatonError:
                report.warnings.append("The X2 didn't answer device/<MAC>/keys_request (S-MQTT-LISTS).")
        dump["mqtt"] = {"activities": acts, "devices": devs, "raw": hub.raw_log}
    finally:
        await hub.stop()


async def listen(settings: Settings, seconds: float, factory: ClientFactory | None = None) -> list[str]:
    """Every message under activity/#, device/# and +/up for a while (for first contact with a real X2)."""
    assert settings.mqtt is not None
    import aiomqtt

    m = settings.mqtt
    heard: list[str] = []
    make = factory or aiomqtt.Client
    async with make(
        m.host, m.port, username=m.username, password=m.password, protocol=aiomqtt.ProtocolVersion.V311
    ) as c:
        for pattern in ("activity/#", "device/#", "+/up"):
            await c.subscribe(pattern)
        with contextlib.suppress(TimeoutError):
            async with asyncio.timeout(seconds):
                async for msg in c.messages:
                    retained = " (retained)" if msg.retain else ""
                    heard.append(f"{msg.topic}{retained}: {msg.payload!r}")
    return heard


async def run_doctor(
    settings: Settings,
    *,
    timeout: float = 5.0,
    dump_dir: Path | None = None,
    listen_s: float = 0.0,
    api: ServerAPI | None = None,
    mqtt_factory: ClientFactory | None = None,
) -> Report:
    report = Report(versions(), list(settings.problems))
    report.unverified_assumptions = [a.id for a in unverified()]
    dump: dict[str, Any] = {}
    mac = settings.mqtt.mac if settings.mqtt else None
    model = None
    if settings.url:
        owned = api is None
        api = api or ServerAPI(settings.url, timeout=timeout)
        try:
            server_mac, model = await _server_checks(settings, api, report, dump)
            mac = server_mac or mac
        finally:
            if owned:
                await api.aclose()
    if settings.mqtt is not None:
        if model in ("X1", "X1S"):
            pass  # warned above: no MQTT on this model, so nothing to probe (it would only time out)
        elif mac is None:
            report.checks.append(
                Check(
                    "mqtt",
                    False,
                    "the X2's MAC is unknown",
                    "Set SOFABATON_MQTT_MAC (or configure sofabaton-x-server).",
                )
            )
        else:
            await _mqtt_checks(settings, mac, report, dump, timeout, mqtt_factory)
        if listen_s and model not in ("X1", "X1S"):
            report.heard = await listen(settings, listen_s, mqtt_factory)
    if not settings.url and settings.mqtt is None:
        report.warnings.append("Nothing configured: set SOFABATON_URL and/or SOFABATON_MQTT_URL.")
    if dump_dir is not None and dump:
        dump_dir.mkdir(parents=True, exist_ok=True)
        dump["_meta"] = {"captured_at": datetime.now(UTC).isoformat(timespec="seconds"), "versions": report.versions}
        path = dump_dir / "sofabaton.json"
        path.write_text(redact(json.dumps(dump, indent=1, default=str)) + "\n")
        report.dumped_to = str(path)
    return report


def render(report: Report) -> str:
    lines = ["Versions: " + ", ".join(f"{k} {v}" for k, v in report.versions.items())]
    if report.config_problems:
        lines.append("FAIL config:")
        lines += [f"     - {p}" for p in report.config_problems]
    else:
        lines.append("OK   config")
    for c in report.checks:
        lines.append(f"{'OK  ' if c.ok else 'FAIL'} {c.step:<9} {c.detail}")
        if c.hint:
            lines.append(f"       -> {c.hint}")
    lines += [f"WARN {w}" for w in report.warnings]
    if report.heard:
        lines.append("Heard on the broker:")
        lines += [f"     {h}" for h in report.heard]
    if report.dumped_to:
        lines.append(f"Dumped to {report.dumped_to}")
    lines.append(
        f"{len(report.unverified_assumptions)} protocol assumptions not yet confirmed on hardware: "
        + ", ".join(report.unverified_assumptions)
        + " (see HARDWARE_VALIDATION.md)"
    )
    lines.append("All checks passed." if report.ok else "Some checks failed; see the -> hints above.")
    return redact("\n".join(lines))


def to_json(report: Report) -> str:
    doc = asdict(report)
    doc["ok"] = report.ok
    return redact(json.dumps(doc, indent=1, default=str))
