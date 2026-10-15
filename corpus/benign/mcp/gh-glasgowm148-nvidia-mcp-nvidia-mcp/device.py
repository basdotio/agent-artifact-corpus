"""Stable library API for other tools that drive the same explicitly configured TV (see docs/library.md).

``Shield`` wraps the MCP server's own transport and operations: the viewing guard, the
quit-then-force-stop rule and the checksum-verified push are the same code the tools run, not
copies. Unlike the MCP tools, ``adb`` and ``rpc`` here are unrestricted, because the caller is a
program, not a model. Never hand them to a model as tools.
"""

import re
import time
from pathlib import Path, PurePosixPath

from .android_tools import sha256_file
from .config import Config, ShieldError
from .diagnostics import app_memory, meminfo, process_deaths
from .operations import KODI, UNATTENDED, Operations
from .transport import KODI_ROUTES, Transport, push_atomic, remote_sha256

__all__ = ["KODI_ROUTES", "UNATTENDED", "Shield"]

# Absolute device paths the file helpers accept: shared storage and adb's scratch directory.
REMOTE_PATH = re.compile(r"/(?:sdcard|storage/emulated/0|data/local/tmp)/[A-Za-z0-9_.,+=@ /-]+")


def remote_path(path):
    path = str(path)
    if (
        not REMOTE_PATH.fullmatch(path)
        or ".." in PurePosixPath(path).parts
        or path.endswith("/")
        or "//" in path
    ):
        raise ShieldError(
            "Device paths must be absolute files under /sdcard, /storage/emulated/0 or "
            "/data/local/tmp, without '..'",
            "invalid_request",
        )
    return path


class Shield:
    """One configured TV (Android by default, Apple TV opt-in). Thread-safe for the guarded operations; use as a context manager
    (or call ``close``) so a Kodi ``adb forward`` is removed."""

    def __init__(self, config: Config, *, kodi_route: str | None = None, transport=None):
        self.config = config
        if config.platform not in ("android", "apple_tv"):
            raise ShieldError("Unknown device platform")
        if config.platform == "apple_tv":
            from .apple_tv import AppleOperations, AppleTransport

            if kodi_route not in (None, "direct"):
                raise ShieldError("Apple TV does not support ADB forwarding", "unsupported")
            self.transport = transport if transport is not None else AppleTransport(config)
            self.operations = AppleOperations(self.transport)
            return
        self.transport = transport if transport is not None else Transport(config, kodi_route)
        self.operations = Operations(self.transport)

    @classmethod
    def from_env(cls, **kwargs):
        """Build from the same environment variables as the MCP server (ANDROID_TV_HOST or SHIELD_HOST, ...)."""
        return cls(Config.from_env(), **kwargs)

    def close(self):
        self.transport.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # Raw access -----------------------------------------------------------------------------

    def adb(self, args, *, timeout: float = 30, limit: int = 1_000_000) -> bytes:
        """Run ``adb -s <serial> <args...>`` with bounded output; raises ShieldError."""
        if isinstance(args, str) or not all(isinstance(a, str) for a in args):
            raise TypeError("adb() takes a list of argument strings")
        return self.transport.adb(*args, timeout=timeout, limit=limit)

    def shell(self, args, *, timeout: float = 30, limit: int = 1_000_000) -> str:
        """``adb shell`` with each argument shell-quoted; returns stripped text."""
        if isinstance(args, str) or not all(isinstance(a, str) for a in args):
            raise TypeError("shell() takes a list of argument strings")
        return self.transport.shell(*args, timeout=timeout, limit=limit)

    def rpc(self, method: str, params: dict | None = None):
        """Kodi JSON-RPC ``method`` over the configured route; returns ``result``."""
        return self.transport.rpc(method, params)

    # Viewing state --------------------------------------------------------------------------

    def viewing_state(self) -> dict:
        """Classify what the TV is doing (see docs/library.md for the fields and verdicts)."""
        return self.operations.viewing_state()

    def kodi_alive(self) -> bool:
        """Android: process running (pidof). Apple TV: Kodi HTTP answers; not process proof."""
        return self.operations.kodi_running()

    # Lifecycle (needs Config.allow_writes) ---------------------------------------------------

    def quit_kodi(self, wait: float = 30) -> dict:
        """Quit Kodi exactly as ``kodi_lifecycle stop`` does: refuse unless nobody is watching,
        send ``Application.Quit``, wait up to ``wait`` seconds, and force-stop only a hung exit
        whose kodi.log proves settings were saved while the guard still passes. Otherwise raises
        ShieldError with kind ``exit_hung`` and leaves Kodi alone. Apple TV never force-stops;
        it reports graceful HTTP disappearance without claiming process termination."""
        ops = self.operations
        with ops.lock:
            ops.writes()
            if self.config.platform == "android" and not ops.kodi_running():
                return {"requested": "stop", "stopped_by": None, "note": "Kodi was not running."}
            previous = ops.quit_wait
            ops.quit_wait = wait
            try:
                return ops.lifecycle("stop")
            finally:
                ops.quit_wait = previous

    def start_kodi(self, wait: float = 0, *, interrupt_other_app: bool = False) -> dict:
        """Start Kodi under the TV guard, as ``kodi_lifecycle start``. With ``wait`` > 0, also
        wait up to that many seconds for Kodi's JSON-RPC to answer (``ready``)."""
        result = self.operations.lifecycle("start", interrupt_other_app=interrupt_other_app)
        if wait > 0:
            deadline = time.monotonic() + wait
            result["ready"] = False
            while time.monotonic() < deadline:
                try:
                    self.transport.rpc("JSONRPC.Ping")
                    result["ready"] = True
                    break
                except ShieldError:
                    time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
        return result

    # Files ----------------------------------------------------------------------------------

    def pull(self, path, local=None, *, limit: int = 50_000_000):
        """Read a device file. Without ``local`` returns its bytes (at most ``limit``); with
        ``local`` streams it to that new private (0600) file and returns the byte count."""
        path = remote_path(path)
        if local is not None:
            return self.transport.download(path, Path(local), limit=limit)
        if not self.transport.is_file(path):
            raise ShieldError("Device file is missing or unreadable", "not_found")
        return self.transport.exec_out(["cat", path], limit=limit, timeout=180)

    def push_verified(
        self, local, remote, *, mode: str | None = None, timeout: float | None = None
    ) -> dict:
        """Upload ``local`` to ``remote`` atomically: push to a temporary file beside it, check
        the temporary file's SHA-256 on the Shield, ``mv`` it into place and check again. A
        failed check leaves the previous file untouched. ``mode`` (octal) defaults to the
        existing file's permissions. ``timeout`` (seconds) bounds the push and defaults to one
        scaled to the file size. Needs Config.allow_writes."""
        self.operations.writes()
        remote = remote_path(remote)
        local = Path(local)
        if local.is_symlink() or not local.is_file():
            raise ShieldError("Choose a regular local file, not a symlink", "invalid_request")
        expected = sha256_file(local)
        if mode is None and self.transport.is_file(remote):
            current = self.transport.shell("stat", "-c", "%a", remote).strip()
            if not re.fullmatch(r"[0-7]{3,4}", current):
                raise ShieldError("Cannot read the existing file's permissions", "device_error")
            mode = format(int(current, 8) & 0o777, "03o")

        def verify(temp):
            if remote_sha256(self.transport, temp) != expected:
                raise ShieldError(
                    "Uploaded copy failed its checksum; the device file was not replaced",
                    "verify_failed",
                )

        push_atomic(self.transport, local, remote, mode=mode, before_commit=verify, timeout=timeout)
        if remote_sha256(self.transport, remote) != expected:
            raise ShieldError("Device file does not match after the move", "verify_failed")
        self.operations.audit("push_verified", remote)
        return {"remote": remote, "sha256": expected, "bytes": local.stat().st_size}

    # Diagnostics ----------------------------------------------------------------------------

    def memory(self) -> dict:
        """System memory and swap from /proc/meminfo, plus Kodi's PSS/native heap when running."""
        totals = meminfo(self.transport.shell("cat", "/proc/meminfo", limit=64_000))
        swap_total, swap_free = totals.get("SwapTotal"), totals.get("SwapFree")
        kodi = None
        if self.kodi_alive():
            kodi = app_memory(self.transport.shell("dumpsys", "meminfo", KODI, limit=500_000))
        return {
            "mem_total_kb": totals.get("MemTotal"),
            "mem_available_kb": totals.get("MemAvailable"),
            "swap_total_kb": swap_total,
            "swap_free_kb": swap_free,
            "swap_used_percent": round(100 * (swap_total - swap_free) / swap_total, 1)
            if swap_total and swap_free is not None
            else None,
            "kodi": kodi,
        }

    def process_deaths(self, package: str = KODI, lines: int = 2000) -> list:
        """``am_proc_died``/``am_kill`` events for ``package`` in Android's event log (for
        example the low-memory killer ending Kodi behind a screensaver)."""
        if not 1 <= lines <= 20_000:
            raise ValueError("lines must be 1-20000")
        events = self.transport.shell(
            "logcat", "-b", "events", "-d", "-t", str(lines), limit=4_000_000
        )
        return process_deaths(events, package)
