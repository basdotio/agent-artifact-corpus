"""Async wrapper around the adb binary. Every call is an argv list; no host shell is involved."""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass

DEFAULT_TIMEOUT = 30.0


class AdbError(RuntimeError):
    """adb exited non-zero or could not be run."""


class AdbTimeout(AdbError):
    """adb did not finish within the timeout."""


@dataclass(frozen=True)
class AdbResult:
    stdout: str
    stderr: str
    returncode: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class Adb:
    """One device, addressed by serial (``host:port`` for TCP devices)."""

    def __init__(self, serial: str, adb_bin: str | None = None) -> None:
        self.serial = serial
        self._bin = adb_bin or shutil.which("adb") or "adb"

    async def _spawn(self, *args: str, timeout: float) -> tuple[bytes, bytes, int]:
        try:
            proc = await asyncio.create_subprocess_exec(
                self._bin,
                "-s",
                self.serial,
                *args,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise AdbError(f"adb binary not found: {self._bin}") from exc
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout)
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise AdbTimeout(f"adb {' '.join(args)[:80]} timed out after {timeout}s") from exc
        return out, err, proc.returncode if proc.returncode is not None else -1

    async def run(
        self, *args: str, timeout: float = DEFAULT_TIMEOUT, check: bool = True
    ) -> AdbResult:
        out, err, code = await self._spawn(*args, timeout=timeout)
        result = AdbResult(out.decode("utf-8", "replace"), err.decode("utf-8", "replace"), code)
        if check and not result.ok:
            detail = (result.stderr or result.stdout).strip()
            raise AdbError(f"adb {' '.join(args)[:80]} failed ({code}): {detail}")
        return result

    async def shell(
        self, command: str, timeout: float = DEFAULT_TIMEOUT, check: bool = True
    ) -> str:
        """Run ``command`` in the device shell and return stdout."""
        return (await self.run("shell", command, timeout=timeout, check=check)).stdout

    async def exec_out(self, *args: str, timeout: float = DEFAULT_TIMEOUT) -> bytes:
        """Binary stdout (screencap and similar)."""
        out, err, code = await self._spawn("exec-out", *args, timeout=timeout)
        if code != 0:
            raise AdbError(f"adb exec-out {' '.join(args)[:80]} failed ({code}): {err.decode()}")
        return out

    async def forward(self, remote: str, local: str = "tcp:0") -> int:
        """Create a host->device forward and return the local TCP port."""
        out = (await self.run("forward", local, remote)).stdout.strip()
        return int(out) if out.isdigit() else int(local.split(":")[1])

    async def forward_list(self) -> list[tuple[str, str]]:
        """(local, remote) pairs of existing forwards for this device."""
        result = await self.run("forward", "--list", check=False)
        pairs = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[0] == self.serial:
                pairs.append((parts[1], parts[2]))
        return pairs

    async def remove_forward(self, local: str) -> None:
        await self.run("forward", "--remove", local, check=False)

    async def push(self, local_path: str, remote_path: str, timeout: float = 300.0) -> None:
        await self.run("push", local_path, remote_path, timeout=timeout)


async def run_adb(adb_bin: str | None, *args: str, timeout: float = 15.0) -> str:
    """Host-level adb command (not bound to one device); returns combined output."""
    binary = adb_bin or shutil.which("adb") or "adb"
    proc = await asyncio.create_subprocess_exec(
        binary, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise AdbTimeout(f"adb {args[0]} timed out after {timeout}s") from exc
    return out.decode("utf-8", "replace")


async def connect_tcp(serial: str, adb_bin: str | None = None, timeout: float = 15.0) -> str:
    """``adb connect`` for host:port serials (no-op for USB serials)."""
    if ":" not in serial:
        return "usb"
    binary = adb_bin or shutil.which("adb") or "adb"
    proc = await asyncio.create_subprocess_exec(
        binary,
        "connect",
        serial,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise AdbTimeout(f"adb connect {serial} timed out after {timeout}s") from exc
    return out.decode("utf-8", "replace").strip()


def parse_devices(output: str) -> list[dict[str, str]]:
    """Rows of ``adb devices [-l]`` output as [{serial, state}]."""
    devices = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and not line.startswith("*"):
            devices.append({"serial": parts[0], "state": parts[1]})
    return devices


def detect_single_device(adb_bin: str | None = None, timeout: float = 8.0) -> str | None:
    """The serial of the only attached device in state ``device``, else None."""
    import subprocess

    binary = adb_bin or shutil.which("adb") or "adb"
    try:
        out = subprocess.run(
            [binary, "devices"], capture_output=True, text=True, timeout=timeout, check=False
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    ready = [d["serial"] for d in parse_devices(out) if d["state"] == "device"]
    return ready[0] if len(ready) == 1 else None


async def list_devices(adb_bin: str | None = None, timeout: float = 15.0) -> list[dict[str, str]]:
    """Host-level ``adb devices -l``: [{serial, state}]."""
    binary = adb_bin or shutil.which("adb") or "adb"
    proc = await asyncio.create_subprocess_exec(
        binary,
        "devices",
        "-l",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise AdbTimeout("adb devices timed out") from exc
    return parse_devices(out.decode("utf-8", "replace"))
