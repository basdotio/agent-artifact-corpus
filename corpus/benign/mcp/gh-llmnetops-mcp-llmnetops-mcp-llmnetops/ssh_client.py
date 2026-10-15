"""Async SSH client for network devices.

Maintains a persistent SSH connection per device and runs each command over
a one-shot exec channel. Exec channels are used instead of a persistent
interactive shell because some devices (e.g. certain MikroTik RouterOS
builds) accept a shell/PTY channel but never emit a prompt or command
output on it, while their exec channel works reliably. Per-session setup
commands (e.g. Cisco 'terminal length 0') are re-applied in the same exec
session as the command they precede.
"""
from __future__ import annotations

import asyncio
import base64
from pathlib import Path

import asyncssh

from .config import APP_CONFIG_DIR, DeviceConfig
from .platforms import Platform


class DeviceError(Exception):
    """Raised when a connection fails or a command times out."""


class DeviceSession:
    """Manages a persistent SSH connection to a single network device."""

    def __init__(self, device: DeviceConfig):
        self.device = device
        self.platform: Platform = device.platform_def
        self._conn: asyncssh.SSHClientConnection | None = None
        self._lock = asyncio.Lock()

    # -- host key handling ---------------------------------------------------

    def _app_known_hosts_path(self) -> Path:
        APP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        return APP_CONFIG_DIR / "known_hosts"

    def _host_in_known_hosts(self, kh_path: Path) -> bool:
        """Return True if the device host already has a trusted key in the file."""
        if not kh_path.is_file() or kh_path.stat().st_size == 0:
            return False
        port = self.device.port if self.device.port != 22 else None
        try:
            trusted, *_ = asyncssh.match_known_hosts(
                str(kh_path), self.device.host, self.device.host, port
            )
        except Exception:
            return False
        return len(trusted) > 0

    def _save_host_key(self, kh_path: Path) -> None:
        """Append the server host key to the known_hosts file (TOFU)."""
        if self._conn is None:
            return
        key = self._conn.get_server_host_key()
        if key is None:
            return
        host = self.device.host
        port = self.device.port
        host_pattern = f"[{host}]:{port}" if port != 22 else host
        line = (
            f"{host_pattern} {key.algorithm.decode()} "
            f"{base64.b64encode(key.public_data).decode()}"
        )
        try:
            with open(kh_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def _host_key_options(self) -> tuple[str | None, bool]:
        """Return (known_hosts arg, should_save_new_key) for the device mode.

        - strict:   verify against the default ~/.ssh/known_hosts
        - no-check: no host key verification
        - auto:     app-managed known_hosts file (TOFU: accept & save new keys)
        """
        mode = self.device.known_hosts
        if mode == "strict":
            return "", False
        if mode == "no-check":
            return None, False
        kh_path = self._app_known_hosts_path()
        if self._host_in_known_hosts(kh_path):
            return str(kh_path), False
        return None, True

    # -- connection setup ----------------------------------------------------

    async def _connect(self) -> None:
        known_hosts, should_save = self._host_key_options()
        kh_path = self._app_known_hosts_path() if should_save else None

        kwargs: dict = dict(
            host=self.device.host,
            port=self.device.port,
            username=self.device.username,
            known_hosts=known_hosts,
        )
        if self.device.ssh_key:
            key = Path(self.device.ssh_key).expanduser()
            if not key.exists():
                raise DeviceError(f"SSH key not found: {key}")
            kwargs["client_keys"] = [str(key)]
        else:
            kwargs["password"] = self.device.password

        try:
            self._conn = await asyncio.wait_for(asyncssh.connect(**kwargs), timeout=20)
        except asyncssh.HostKeyNotVerifiable as e:
            raise DeviceError(
                f"Host key verification failed for {self.device.host}: {e}"
            ) from e
        except (OSError, asyncssh.Error, asyncio.TimeoutError) as e:
            raise DeviceError(
                f"Cannot connect to {self.device.host}:{self.device.port}: {e}"
            ) from e

        if should_save and kh_path is not None:
            self._save_host_key(kh_path)

    async def _ensure_conn(self) -> None:
        """Open the SSH connection if it is not already open."""
        if self._conn is None or self._conn.is_closed():
            await self._connect()

    async def _run_exec(self, command: str, timeout: float) -> str:
        """Run a single command over an exec channel and return its output.

        Uses a one-shot exec channel rather than a persistent interactive
        shell. Some devices (e.g. certain MikroTik RouterOS builds) accept a
        shell/PTY channel but never emit a prompt or command output on it,
        while their exec channel works reliably. Exec also avoids the
        fragility of prompt-pattern matching.
        """
        full_command = command
        if self.platform.setup_commands:
            # Re-apply per-session setup (e.g. disable paging) in the same
            # exec session so it takes effect for this command.
            full_command = "\n".join(self.platform.setup_commands) + "\n" + command
        try:
            result = await asyncio.wait_for(
                self._conn.run(full_command, check=False),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise DeviceError(
                f"Command '{command}' timed out after {timeout:.0f}s on "
                f"{self.device.name}"
            ) from None
        out = result.stdout or ""
        if result.stderr:
            out = f"{out}\n{result.stderr}".strip("\n") if out else result.stderr
        return out.strip()

    # -- public API --------------------------------------------------------------

    async def connect(self) -> None:
        """Establish the SSH connection (idempotent)."""
        async with self._lock:
            await self._ensure_conn()

    async def run(self, command: str, timeout: float | None = None) -> str:
        """Run a command on the device and return its output."""
        async with self._lock:
            await self._ensure_conn()
            timeout = timeout or self.device.timeout
            try:
                return await self._run_exec(command, timeout=timeout)
            except (asyncssh.Error, OSError, ConnectionError):
                # Drop the session so the next call reconnects cleanly.
                await self.close()
                raise

    async def close(self) -> None:
        """Close the connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None
