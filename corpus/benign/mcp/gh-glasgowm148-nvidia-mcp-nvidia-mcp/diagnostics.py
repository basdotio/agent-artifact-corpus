"""Independent transport readiness and bounded, optional Android health telemetry."""

import platform
import re
import shutil
from pathlib import Path

from . import __version__
from .android_tools import signer_command
from .config import ShieldError
from .operation_records import REASONS, clean, next_step, safe_number

REMEDIES = {
    "authorization_required": "Select Allow on the TV debugging prompt (or re-pair Wireless debugging), then reconnect.",
    "authentication_denied": "Check this service's credentials; Kodi HTTP and Manager use separate credentials.",
    "offline": "Reconnect the configured TV; do not restart anything while someone is viewing.",
    "unreachable": "Check the configured IP/port and that this service is enabled on the TV.",
    "missing_dependency": "The agent should install/configure the required computer tool.",
    "permission_denied": "Check executable permissions on the computer or access to the selected Android file.",
    "timeout": "Service did not answer in time. Retry a read later; do not repeat writes automatically.",
    "write_disabled": "Kodi Manager Write Mode is off; the user can turn it on in its settings on the TV.",
    "unsupported": "The installed Kodi Manager is older than this tool needs; core tools still work.",
}


def readiness(ops):
    kodi_version = {}

    def probe(function):
        try:
            if function() is False:
                raise ShieldError("Service readiness could not be established", "invalid_response")
            return {"state": "ready"}
        except ShieldError as exc:
            return {
                "state": exc.kind,
                "reason_code": exc.reason_code,
                "message": str(exc),
                "next_step": REMEDIES.get(
                    exc.kind,
                    "Inspect the relevant service's bounded diagnostics before making changes.",
                ),
            }

    def kodi():
        response = ops.t.rpc("Application.GetProperties", {"properties": ["name", "version"]})
        version = response.get("version") if isinstance(response, dict) else None
        if isinstance(version, dict):
            kodi_version.update(
                {
                    k: v
                    for k, v in version.items()
                    if k in ("major", "minor", "revision")
                    and type(v) is int
                    and 0 <= v <= 1000000000
                }
            )
        return (
            isinstance(response, dict)
            and response.get("name") == "Kodi"
            and isinstance(response.get("version"), dict)
        )

    if ops.c.platform == "apple_tv":
        from .apple_tv import apple_capabilities

        return ops.safe(
            {
                "platform": "apple_tv",
                "adb": {"state": "unsupported"},
                "apple_tv": probe(lambda: bool(ops.t.apple.snapshot())),
                "kodi_http": probe(kodi),
                "versions": {"kodi": kodi_version},
                "manager": probe(lambda: ops.state())
                if ops.c.manager_token
                else {
                    "state": "not_configured",
                    "next_step": "Install/configure Kodi Manager 0.7.17+ for skin/settings/file management",
                },
                "capabilities": apple_capabilities(ops.c),
                "note": "Readiness is separate from idle playback and active Kodi; unknown state blocks changes.",
            }
        )
    result = {
        "adb": probe(lambda: ops.t.adb("get-state").decode().strip() == "device"),
        "kodi_http": probe(kodi),
        "versions": {"kodi": kodi_version},
        "manager": probe(lambda: isinstance(ops.t.manager("/api/health"), dict))
        if ops.c.manager_token
        else {
            "state": "not_configured",
            "next_step": "Optional; core ADB/Kodi tools work without Manager.",
        },
        "capabilities": {
            "writes_enabled": ops.c.allow_writes,
            "plugin_browse_enabled": ops.c.allow_plugin_browse,
            "http_route": getattr(ops.t, "kodi_route", ops.c.http_route),
        },
        "note": "Ready means this service answered now. It does not prove the TV is idle or an account is authenticated.",
    }

    def exists(command):
        return bool(shutil.which(command)) or Path(command).is_file()

    try:
        signer = signer_command(ops.c)
        sign = all(exists(command) for command in (signer[0], signer[-1]) if command != "-jar")
    except ShieldError:
        sign = False
    result["apk_tools"] = {
        "aapt2_available": exists(ops.c.aapt2_path),
        "apksigner_available": sign,
        "note": "Availability only; actual APK inspection verifies tool execution and signatures.",
    }
    return ops.safe(result)


def support_bundle(ops):
    """Versioned field projection; never include raw readiness messages or Manager bodies."""
    ready = readiness(ops)
    bundle = {
        "schema_version": 1,
        "versions": {"nvidia_mcp": __version__, "python": platform.python_version()},
        "capabilities": {
            "operation_record_version": 1,
            "writes_enabled": ops.c.allow_writes,
            "plugin_browse_enabled": ops.c.allow_plugin_browse,
        },
        "readiness": {
            key: {
                "state": value.get("state")
                if value.get("state") in REASONS | {"ready"}
                else "unknown",
                "reason_code": value.get("reason_code", value.get("state"))
                if value.get("reason_code", value.get("state")) in REASONS | {"ready"}
                else "unknown",
                "next_step": next_step(value.get("reason_code", value.get("state")))
                if value.get("state") != "ready"
                else "",
            }
            for key, value in ready.items()
            if key in ("adb", "apple_tv", "kodi_http", "manager")
            and isinstance(value, dict)
            # ADB does not apply to Apple TV; its "unsupported" state is not a problem to fix.
            and not (key == "adb" and ops.c.platform == "apple_tv")
        },
        "history": ops.history.summary(),
        "operations": ops.history.selected(20),
    }
    bundle["versions"]["kodi"] = ready.get("versions", {}).get("kodi", {})
    if ops.c.manager_token:
        try:
            health = ops.t.manager("/api/health")
            capabilities = health.get("diagnostics") if isinstance(health, dict) else None
            if (
                not isinstance(capabilities, dict)
                or capabilities.get("support_bundle_version") != 1
            ):
                bundle["manager"] = {
                    "reason_code": "unsupported",
                    "next_step": next_step("unsupported"),
                }
            else:
                remote = ops.t.manager("/api/diagnostics/support")
                if not isinstance(remote, dict) or remote.get("schema_version") != 1:
                    raise ShieldError("Unknown support bundle version", "invalid_response")
                rows = remote.get("operations", [])
                rows = (
                    [
                        row
                        for row in (clean(r) for r in rows[:20])
                        if row
                        and not any(secret and secret in str(row) for secret in ops.known_secrets)
                    ]
                    if isinstance(rows, list)
                    else []
                )
                metrics = remote.get("metrics", {})
                versions = remote.get("versions", {})
                manager_version = versions.get("manager", "") if isinstance(versions, dict) else ""
                bundle["manager"] = {
                    "schema_version": 1,
                    "operations": rows,
                    "metrics": {
                        k: safe_number(metrics.get(k))
                        for k in ("t", "mk", "ma", "mt", "rc", "rf", "rp")
                    }
                    if isinstance(metrics, dict)
                    else {},
                }
                if isinstance(manager_version, str) and re.fullmatch(
                    r"[0-9]+(?:\.[0-9]+){1,3}", manager_version
                ):
                    bundle["manager"]["version"] = manager_version
        except ShieldError as exc:
            code = exc.reason_code if exc.reason_code in REASONS else "unknown"
            bundle["manager"] = {"reason_code": code, "next_step": next_step(code)}
    rows = bundle["operations"] + bundle.get("manager", {}).get("operations", [])
    bundle["failures"] = [
        {
            "reason_code": r["reason_code"],
            "outcome": r["outcome"],
            "operation_id": r["operation_id"],
            "correlation_id": r["correlation_id"],
            "next_step": next_step(
                "outcome_unknown" if r["outcome"] == "unknown" else r["reason_code"]
            ),
        }
        for r in rows
        if r["outcome"] != "succeeded"
    ][:40]
    return bundle


def meminfo(text):
    """``/proc/meminfo`` totals in kB: MemTotal, MemAvailable, SwapTotal and SwapFree when present."""
    return {
        key: int(value)
        for key, value in re.findall(
            r"^(MemTotal|MemAvailable|SwapTotal|SwapFree):\s*(\d+)\s*kB", text, re.M
        )
    }


def app_memory(text):
    """``dumpsys meminfo <package>`` App Summary in kB (PSS, native heap, RSS), or None."""
    pss = re.search(r"^\s*TOTAL PSS:\s*(\d+)", text, re.M)
    if not pss:
        return None
    native = re.search(r"^\s*Native Heap:\s*(\d+)", text, re.M)
    rss = re.search(r"TOTAL RSS:\s*(\d+)", text)
    return {
        "pss_kb": int(pss[1]),
        "native_heap_kb": int(native[1]) if native else None,
        "rss_kb": int(rss[1]) if rss else None,
    }


# Android event-log records of a process ending: am_proc_died [user,pid,name,oom_adj,proc_state]
# and am_kill [user,pid,name,oom_adj,reason].
PROCESS_EVENT = re.compile(
    r"^(?P<time>\d\d-\d\d \d\d:\d\d:\d\d\.\d+)\s.*?\b(?P<event>am_proc_died|am_kill)\s*:\s*"
    r"\[\d+,(?P<pid>\d+),(?P<name>[^,\]]+),(?P<adj>-?\d+),(?P<detail>[^\]]*)\]",
    re.M,
)


def process_deaths(events, package):
    """``am_proc_died``/``am_kill`` records for ``package`` from ``logcat -b events``, oldest first."""
    found = []
    for m in PROCESS_EVENT.finditer(events):
        if m["name"] != package:
            continue
        row = {
            "time": m["time"],
            "event": m["event"],
            "pid": int(m["pid"]),
            "oom_adj": int(m["adj"]),
        }
        if m["event"] == "am_proc_died" and m["detail"].isdigit():
            row["proc_state"] = int(m["detail"])
        else:
            row["reason"] = m["detail"][:200]
        found.append(row)
    return found


def health(memory, storage, uptime, thermal):
    metrics = meminfo(memory)
    status = re.search(r"Thermal Status:\s*(\d+)", thermal, re.I)
    temperatures = []
    if "Current temperatures from HAL:" in thermal:
        thermal = thermal.split("Current temperatures from HAL:", 1)[1].split(
            "Current cooling devices from HAL:", 1
        )[0]
    for line in thermal.splitlines():
        match = re.search(
            r"Temperature\{mValue=([\d.]+),\s*mType=(\d+),\s*mName=([^,}]+),\s*mStatus=(\d+)", line
        )
        if match and int(match[2]) in (0, 1):
            temperatures.append(
                {
                    "type": "cpu" if match[2] == "0" else "gpu",
                    "celsius": float(match[1]),
                    "status": int(match[4]),
                }
            )
    try:
        seconds = float(uptime.split()[0])
    except (ValueError, IndexError):
        seconds = None
    free = []
    for line in storage.splitlines()[1:]:
        values = line.split()
        if len(values) >= 6 and values[1].isdigit() and values[3].isdigit():
            free.append(
                {"mount": values[-1], "total_kb": int(values[1]), "available_kb": int(values[3])}
            )
    return {
        "memory_kb": metrics or None,
        "storage": free or None,
        "uptime_seconds": seconds,
        "thermal_status": int(status[1]) if status else None,
        "temperatures": temperatures,
        "note": "Missing telemetry is unavailable, not healthy. Android thermal status 0 means none; 1–6 indicate increasing throttling.",
    }
