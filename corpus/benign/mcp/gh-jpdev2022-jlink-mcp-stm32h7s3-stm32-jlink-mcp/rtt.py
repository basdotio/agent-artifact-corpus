from __future__ import annotations

import socket
import threading
import time
from typing import Any

from .config import Config
from .errors import MCPError
from .probe.jlink import SubprocessRunner


class RttSession:
    """J-Link RTT TELNET transport for RTT channel 0.

    The J-Link RTT Client is a thin TELNET client. This class implements the same
    local TELNET transport directly so the MCP server can expose bounded read/write
    operations without trying to parse an interactive terminal process.

    A live J-Link debug connection must exist separately. The service starts a
    J-Link GDB Server as the persistent RTT host when no GDB debug session already
    owns the probe.
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._socket: socket.socket | None = None
        self._lock = threading.RLock()
        self._host_process = None
        self._owns_host = False

    @property
    def connected(self) -> bool:
        return self._socket is not None

    @property
    def host_owned(self) -> bool:
        return self._owns_host

    def attach_socket(self, host: str, port: int, timeout: float = 3.0) -> dict[str, Any]:
        with self._lock:
            self.disconnect_socket()
            try:
                sock = socket.create_connection((host, port), timeout=timeout)
                sock.settimeout(timeout)
            except OSError as exc:
                raise MCPError(
                    f"Unable to connect to J-Link RTT TELNET at {host}:{port}: {exc}",
                    "RTT_CONNECT_FAILED",
                ) from exc
            self._socket = sock
            # Select RTT channel 0. SEGGER's TELNET configuration string is optional,
            # but explicitly selecting channel 0 makes the MCP behavior deterministic.
            try:
                sock.sendall(b"$$SEGGER_TELNET_ConfigStr=RTTCh;0$$")
            except OSError as exc:
                self.disconnect_socket()
                raise MCPError(f"RTT channel setup failed: {exc}", "RTT_CONNECT_FAILED") from exc
            return {"connected": True, "host": host, "port": port, "channel": 0}

    def read(self, max_bytes: int = 4096, timeout_s: float = 0.25) -> dict[str, Any]:
        if max_bytes <= 0 or max_bytes > self.cfg.rtt.max_read_bytes:
            raise MCPError(
                f"max_bytes must be 1..{self.cfg.rtt.max_read_bytes}",
                "INVALID_ARGUMENT",
            )
        with self._lock:
            if self._socket is None:
                raise MCPError("RTT is not connected", "RTT_NOT_CONNECTED")
            old_timeout = self._socket.gettimeout()
            try:
                self._socket.settimeout(timeout_s)
                data = self._socket.recv(max_bytes)
            except socket.timeout:
                data = b""
            except OSError as exc:
                self.disconnect_socket()
                raise MCPError(f"RTT read failed: {exc}", "RTT_READ_FAILED") from exc
            finally:
                if self._socket is not None:
                    self._socket.settimeout(old_timeout)
            if data == b"":
                # A zero-length read can mean timeout or a clean remote close depending
                # on the socket implementation. Preserve the connection for the common
                # polling/timeout case; EOF is detected on the next read or explicit close.
                return {"bytes": 0, "data_hex": "", "text": "", "timeout": True}
            return {
                "bytes": len(data),
                "data_hex": data.hex(),
                "text": data.decode("utf-8", errors="replace"),
                "timeout": False,
            }

    def write(self, data: bytes) -> dict[str, Any]:
        if not data:
            raise MCPError("RTT write data must not be empty", "INVALID_ARGUMENT")
        if len(data) > self.cfg.rtt.max_write_bytes:
            raise MCPError(
                f"RTT write exceeds {self.cfg.rtt.max_write_bytes} bytes",
                "RTT_WRITE_TOO_LARGE",
            )
        with self._lock:
            if self._socket is None:
                raise MCPError("RTT is not connected", "RTT_NOT_CONNECTED")
            try:
                self._socket.sendall(data)
            except OSError as exc:
                self.disconnect_socket()
                raise MCPError(f"RTT write failed: {exc}", "RTT_WRITE_FAILED") from exc
            return {"written": len(data), "data_hex": data.hex()}

    def disconnect_socket(self) -> None:
        if self._socket is not None:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def set_host_process(self, process: Any, owns_host: bool) -> None:
        self._host_process = process
        self._owns_host = owns_host

    def stop_host(self) -> None:
        self.disconnect_socket()
        if self._owns_host and self._host_process is not None:
            proc = self._host_process
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except Exception:
                    proc.kill()
            self._host_process = None
        self._owns_host = False

    def status(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "host_owned": self._owns_host,
            "telnet_host": self.cfg.rtt.host,
            "telnet_port": self.cfg.rtt.telnet_port,
            "channel": 0,
            "control_block": self.cfg.rtt.control_block,
            "search_ranges": self.cfg.rtt.search_ranges,
        }
