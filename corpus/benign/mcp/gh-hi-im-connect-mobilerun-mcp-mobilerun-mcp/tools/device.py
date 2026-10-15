"""Device status and connection management."""

from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from .. import adb as adb_mod
from ..errors import fail
from ..parsers import system as sysparse
from ..parsers.media import parse_stream_block
from ..session import Runtime
from . import cloud
from .common import Device, get_session
from .legacy import _mobilerun_bin as legacy_bin


def register(mcp: FastMCP, rt: Runtime) -> None:
    @mcp.tool(tags={"read"})
    async def get_device_status(device: Device = None) -> dict:
        """Battery, screen power, foreground app, size, storage, network addresses, volume."""
        session = get_session(rt, device)
        if not session.has_adb:
            await session.ensure_connected()
            width, height = await session.screen_size()
            return {
                "serial": session.serial,
                "kind": session.target.kind,
                "platform": session.target.platform,
                "screen": {"size": [width, height]},
                "foreground": {"package": await session.core.call("current_app_id")},
                "capabilities": await session.core.capabilities(),
            }
        (battery, size, density, wake, focus, storage, ip, props, audio) = await asyncio.gather(
            session.shell("dumpsys battery"),
            session.shell("wm size"),
            session.shell("wm density"),
            session.shell("dumpsys power | grep -E 'mWakefulness='"),
            session.shell("dumpsys window | grep -E 'mCurrentFocus'"),
            session.shell("df /data"),
            session.shell("ip -4 addr show"),
            session.shell(
                "getprop | grep -E 'ro.product.model|ro.build.version.release|ro.build.version.sdk|ro.product.cpu.abi\\]'"
            ),
            session.shell("dumpsys audio | grep -A8 -E '^- STREAM_MUSIC'"),
        )
        prop = sysparse.parse_getprop(props)
        foreground = sysparse.parse_focus(focus)
        return {
            "serial": session.serial,
            "model": prop.get("ro.product.model"),
            "android": prop.get("ro.build.version.release"),
            "sdk": prop.get("ro.build.version.sdk"),
            "abi": prop.get("ro.product.cpu.abi"),
            "screen": {
                "size": sysparse.parse_wm_size(size),
                "density": sysparse.parse_wm_density(density),
                "power": sysparse.parse_wakefulness(wake),
            },
            "foreground": {"package": foreground[0], "activity": foreground[1]}
            if foreground
            else None,
            "battery": sysparse.parse_battery(battery),
            "storage": sysparse.parse_df(storage),
            "addresses": sysparse.parse_ip_addresses(ip),
            "music_volume": parse_stream_block(audio),
            "portal_transport": session.portal.transport,
        }

    @mcp.tool(tags={"read"})
    async def list_devices(
        scope: str = "local",
        state: list[str] | None = None,
        type: str | None = None,
        name: str | None = None,
        country: str | None = None,
        page: int | None = None,
        pageSize: int | None = None,
        filters: dict | None = None,
    ) -> dict:
        """Devices you can control. scope: local (adb devices) | cloud (Mobilerun Cloud, needs
        MOBILERUN_CLOUD_API_KEY) | all. Cloud filters: state (creating, assigned, ready,
        terminated, ...), type, name, country, page, pageSize (or a filters dict).
        Any listed id works as the device argument of every tool."""
        if scope not in ("local", "cloud", "all"):
            fail("invalid_argument", "scope must be local, cloud or all")
        cloud_args = {
            "state": state,
            "type": type,
            "name": name,
            "country": country,
            "page": page,
            "pageSize": pageSize,
            **(filters or {}),
        }
        if any(v is not None for v in cloud_args.values()) and scope == "local":
            scope = "cloud"
        result: dict = {"default": rt.config.device or None}
        if scope in ("local", "all"):
            try:
                devices = await adb_mod.list_devices(rt.config.adb_bin)
            except adb_mod.AdbError as exc:
                if scope == "local":
                    fail("device_unreachable", str(exc))
                devices = []
            result.update(count=len(devices), devices=devices)
        if scope in ("cloud", "all"):
            if scope == "all" and not rt.config.cloud_api_key:
                result["cloud"] = {"skipped": "MOBILERUN_CLOUD_API_KEY is not set"}
            else:
                result["cloud"] = await cloud.cloud_list_devices(
                    rt, **{k: v for k, v in cloud_args.items() if v is not None}
                )
        return result

    @mcp.tool(tags={"read"})
    async def ping_device(device: Device = None) -> dict:
        """Is the device reachable? For adb devices, reports the Portal transport
        (http or content_provider)."""
        session = get_session(rt, device)
        await session.ensure_connected()
        if not session.has_adb:
            return {"ok": True, "serial": session.serial, "kind": session.target.kind}
        try:
            return {"ok": True, "serial": session.serial, **await session.portal.ping()}
        except Exception as exc:  # portal errors surface as a clear failure, not a stack trace
            fail("device_unreachable", f"{session.serial}: {exc}")

    @mcp.tool(tags={"write"})
    async def connect_device(device: Device = None) -> dict:
        """(Re)connect adb and the Portal for a device; use after the network path came back."""
        session = get_session(rt, device)
        session._connected = False
        await session.ensure_connected()
        transport = session.portal.transport if session.portal else session.target.kind
        return {"ok": True, "serial": session.serial, "portal_transport": transport}

    @mcp.tool(tags={"write"})
    async def disconnect_device(device: Device = None) -> dict:
        """Disconnect a TCP/IP adb device (adb disconnect host:port) and drop its session."""
        session = get_session(rt, device)
        if not session.has_adb or ":" not in session.serial:
            fail("unsupported", f"{session.serial} is not a TCP/IP adb device")
        out = await adb_mod.run_adb(rt.config.adb_bin, "disconnect", session.serial)
        await rt.drop(session.serial)
        return {"ok": True, "serial": session.serial, "output": out.strip()}

    async def mobilerun_cli(*args: str, timeout: float = 300.0) -> dict:
        binary = legacy_bin(rt.config.mobilerun_bin)
        proc = await asyncio.create_subprocess_exec(
            binary, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            fail("timeout", f"mobilerun {args[0]} exceeded {timeout:.0f}s")
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "output": out.decode("utf-8", "replace")[-4000:],
        }

    @mcp.tool(tags={"write"})
    async def setup_portal(path: str | None = None, device: Device = None) -> dict:
        """Install and enable the Mobilerun Portal on the device (mobilerun setup); path installs
        a specific Portal APK."""
        session = get_session(rt, device)
        args = ["setup", "-d", session.serial] + (["--path", path] if path else [])
        return await mobilerun_cli(*args)

    @mcp.tool(tags={"read"})
    async def doctor(device: Device = None) -> dict:
        """Health check of adb, the Portal and the device (mobilerun doctor)."""
        args = ["doctor"] + (["-d", get_session(rt, device).serial] if device else [])
        return await mobilerun_cli(*args, timeout=120.0)

    @mcp.tool(tags={"read"})
    async def request_screen_capture_permission(device: Device = None) -> dict:
        """Compatibility no-op: screenshots use the Portal / adb screencap, no prompt is needed."""
        return {"needed": False, "message": "screen capture works over adb; nothing to approve"}

    @mcp.tool(tags={"read"})
    async def echo(text: str | None = None, message: str = "") -> dict:
        """Returns text verbatim: a check that the MCP transport is alive (no device access)."""
        value = text if text is not None else message
        return {
            "echo": value,
            "text": value,
            "policy": rt.config.policy,
            "scopes": sorted(rt.config.scopes),
        }
