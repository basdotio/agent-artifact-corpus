from __future__ import annotations

import socket
import time
from pathlib import Path
from typing import Any

from pygdbmi.gdbcontroller import GdbController

from ..config import Config
from ..errors import MCPError
from ..probe.jlink import SubprocessRunner


class GdbSession:
    def __init__(self, cfg: Config, runner: SubprocessRunner):
        self.cfg = cfg
        self.runner = runner
        self.server_process = None
        self.gdb: GdbController | None = None
        self.elf: str | None = None

    def start(self, elf: str | None = None) -> dict[str, Any]:
        if self.gdb is not None:
            raise MCPError("GDB session is already active", "GDB_ALREADY_RUNNING")
        server_exe = self.runner.resolve(self.cfg.executables.gdb_server)
        args = [
            server_exe,
            "-device", self.cfg.target.device,
            "-if", self.cfg.target.interface,
            "-speed", str(self.cfg.target.speed_khz),
            "-port", str(self.cfg.debug.gdb_port),
            "-localhostonly", "1",
            "-silent",
            "-RTTTelnetPort", str(self.cfg.rtt.telnet_port),
        ]
        if self.cfg.target.jlink_serial is not None:
            args += ["-USB", str(self.cfg.target.jlink_serial)]
        import subprocess
        self.server_process = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.monotonic() + self.cfg.debug.gdb_startup_timeout_s
        while time.monotonic() < deadline:
            if self.server_process.poll() is not None:
                output = self.server_process.stdout.read() if self.server_process.stdout else ""
                raise MCPError(
                    f"J-Link GDB Server exited during startup: {output[-2000:]}",
                    "GDB_SERVER_FAILED",
                )
            try:
                with socket.create_connection(("127.0.0.1", self.cfg.debug.gdb_port), timeout=0.2):
                    break
            except OSError:
                time.sleep(self.cfg.debug.gdb_poll_interval_s)
        else:
            raise MCPError("Timed out waiting for J-Link GDB Server TCP port", "GDB_SERVER_TIMEOUT")

        gdb_exe = self.runner.resolve(self.cfg.executables.gdb)
        self.gdb = GdbController(
            command=[gdb_exe, "--interpreter=mi3", "--quiet"],
            time_to_check_for_additional_output_sec=self.cfg.debug.gdb_poll_interval_s,
        )
        self.command(
            f"-target-select extended-remote :{self.cfg.debug.gdb_port}"
        )
        if elf:
            self.load_elf(elf)
        return {"gdb_port": self.cfg.debug.gdb_port, "elf": self.elf}

    def load_elf(self, elf: str) -> dict[str, Any]:
        path = Path(elf).expanduser().resolve()
        if not path.is_file():
            raise MCPError(f"ELF does not exist: {path}", "ELF_NOT_FOUND")
        self.command(f'-file-exec-and-symbols "{path}"')
        self.elf = str(path)
        return {"elf": self.elf}

    def command(self, command: str) -> list[dict[str, Any]]:
        if self.gdb is None:
            raise MCPError("GDB session is not running", "GDB_NOT_RUNNING")
        try:
            return self.gdb.write(command, timeout_sec=self.cfg.debug.gdb_command_timeout_s)
        except Exception as exc:
            raise MCPError(f"GDB command failed: {exc}", "GDB_COMMAND_FAILED") from exc

    def stop(self) -> None:
        if self.gdb is not None:
            try:
                self.gdb.exit()
            except Exception:
                pass
            self.gdb = None
        if self.server_process is not None:
            if self.server_process.poll() is None:
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=3)
                except Exception:
                    self.server_process.kill()
            self.server_process = None
        self.elf = None
