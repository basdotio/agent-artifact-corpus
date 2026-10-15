from __future__ import annotations

import threading
from contextlib import contextmanager

from .config import Config
from .errors import MCPError
from .models import TargetState
from .probe.jlink import JLinkBackend


class DebugSession:
    """Coordinates low-level J-Link ownership and target state.

    JLinkExe is one-shot, but its target connection is still logically shared with the
    GDB server. This object prevents overlapping operations and blocks low-level J-Link
    access while GDB owns the target.
    """

    def __init__(self, cfg: Config, jlink: JLinkBackend):
        self.cfg = cfg
        self.jlink = jlink
        self.state = TargetState.DISCONNECTED
        self.gdb_active = False
        self._lock = threading.RLock()

    @contextmanager
    def operation(self, *, allow_with_gdb: bool = False):
        with self._lock:
            if self.gdb_active and not allow_with_gdb:
                raise MCPError(
                    "GDB owns the target; stop the GDB session before using direct J-Link operations",
                    "TARGET_OWNED_BY_GDB",
                )
            yield

    def mark_connected(self) -> None:
        self.state = TargetState.CONNECTED

    def mark_halted(self) -> None:
        self.state = TargetState.HALTED

    def mark_running(self) -> None:
        self.state = TargetState.RUNNING

    def mark_disconnected(self) -> None:
        self.state = TargetState.DISCONNECTED
        self.gdb_active = False

    def acquire_gdb(self) -> None:
        with self._lock:
            if self.gdb_active:
                raise MCPError("GDB session is already active", "GDB_ALREADY_RUNNING")
            self.gdb_active = True

    def release_gdb(self) -> None:
        with self._lock:
            self.gdb_active = False
