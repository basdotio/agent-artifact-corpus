from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..config import Config
from ..errors import MCPError
from .backend import CommandResult


class SubprocessRunner:
    def resolve(self, executable: str) -> str:
        if Path(executable).is_absolute():
            if Path(executable).is_file():
                return executable
            raise MCPError(f"Executable not found: {executable}", "EXECUTABLE_NOT_FOUND")
        resolved = shutil.which(executable)
        if resolved:
            return resolved
        raise MCPError(f"Executable not found: {executable}", "EXECUTABLE_NOT_FOUND")

    def run(
        self,
        executable: str,
        args: list[str],
        stdin: str | None = None,
        timeout: float = 60,
    ) -> CommandResult:
        exe = self.resolve(executable)
        try:
            completed = subprocess.run(
                [exe, *args],
                input=stdin,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise MCPError(f"Command timed out: {exe}", "COMMAND_TIMEOUT") from exc
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)


class JLinkBackend:
    """One-shot J-Link Commander backend.

    The backend deliberately does not keep JLinkExe alive. A higher-level session manager
    serializes access and prevents this backend from being used concurrently with GDB.
    """

    def __init__(self, cfg: Config, runner: SubprocessRunner | None = None):
        self.cfg = cfg
        self.runner = runner or SubprocessRunner()

    def _args(self) -> list[str]:
        t = self.cfg.target
        args = ["-device", t.jlink_device, "-if", t.interface, "-speed", str(t.speed_khz)]
        if t.jlink_serial is not None:
            # SEGGER documents -SelectEmuBySN for Commander.
            args += ["-USB", str(t.jlink_serial)]
        return args

    def execute(self, commands: list[str], timeout: float = 60) -> str:
        script = "\n".join(commands + ["exit"]) + "\n"
        result = self.runner.run(self.cfg.executables.jlink, self._args(), script, timeout)
        output = result.output
        if result.returncode != 0:
            raise MCPError(output or "J-Link Commander failed", "JLINK_FAILED")
        # J-Link can print a successful-looking transcript while reporting a target connection
        # problem. Keep parsing centralized and let callers inspect the transcript as evidence.
        return output

    def connect(self) -> dict[str, Any]:
        out = self.execute(["connect"], 30)
        return {"connected": True, "output": tail(out)}

    def status(self) -> dict[str, Any]:
        out = self.execute(["connect", "regs"], 30)
        return {"connected": True, "register_output": tail(out)}

    def reset(self, *, run_after: bool = True) -> dict[str, Any]:
        commands = ["connect", "reset"]
        if run_after:
            commands.append("go")
        return {"output": tail(self.execute(commands, 30))}

    def halt(self) -> dict[str, Any]:
        return {"output": tail(self.execute(["connect", "halt"], 30))}

    def run(self) -> dict[str, Any]:
        return {"output": tail(self.execute(["connect", "go"], 30))}

    def step(self) -> dict[str, Any]:
        return {"output": tail(self.execute(["connect", "halt", "step", "regs"], 30))}

    def registers(self) -> dict[str, Any]:
        return {"output": tail(self.execute(["connect", "regs"], 30), 8000)}

    def identify(self) -> dict[str, Any]:
        out = self.execute(["connect"], 30)
        return {"device": self.cfg.target.device, "interface": self.cfg.target.interface, "output": tail(out)}

    def read_memory(self, address: int, length: int) -> dict[str, Any]:
        if length <= 0:
            raise MCPError("length must be positive", "INVALID_ARGUMENT")
        out = self.execute(["connect", f"mem8 0x{address:X}, {length}"], 30)
        data = parse_mem8(out, length)
        if len(data) != length:
            raise MCPError(
                f"J-Link returned {len(data)} bytes, expected {length}",
                "MEMORY_READ_INCOMPLETE",
            )
        return {"address": f"0x{address:08X}", "length": length, "data_hex": data.hex()}

    def write_memory(self, address: int, data: bytes) -> dict[str, Any]:
        if not data:
            raise MCPError("data must not be empty", "INVALID_ARGUMENT")
        commands = ["connect"]
        # Use byte writes for the final 1-3 bytes so the command never writes beyond the
        # requested range. For aligned 4-byte chunks use w4 for efficiency.
        offset = 0
        while offset + 4 <= len(data):
            value = int.from_bytes(data[offset:offset + 4], "little")
            commands.append(f"w4 0x{address + offset:X}, 0x{value:08X}")
            offset += 4
        while offset < len(data):
            commands.append(f"w1 0x{address + offset:X}, 0x{data[offset]:02X}")
            offset += 1
        out = self.execute(commands, 60)
        return {"address": f"0x{address:08X}", "length": len(data), "output": tail(out)}

    def write_register(self, name: str, value: int) -> dict[str, Any]:
        out = self.execute(["connect", f'wreg "{name}", 0x{value:X}'], 30)
        return {"register": name, "value": f"0x{value:X}", "output": tail(out)}

    def program(self, image: str, address: int | None = None, *, reset_after: bool = True) -> dict[str, Any]:
        path = Path(image).expanduser().resolve()
        if not path.is_file():
            raise MCPError(f"Image does not exist: {path}", "IMAGE_NOT_FOUND")
        suffix = path.suffix.lower()
        if suffix == ".bin" and address is None:
            raise MCPError("A destination address is required for .bin images", "INVALID_ARGUMENT")
        command = f'loadfile "{path}"'
        if address is not None:
            command += f" 0x{address:X}"
        # LoadFile resets by default. Only add the documented noreset modifier when requested.
        if not reset_after:
            if address is None:
                command += " 0 noreset"
            else:
                command += " noreset"
        out = self.execute(["connect", command], 900)
        return {"image": str(path), "address": address, "output": tail(out, 10000)}

    def verify_bin(self, image: str, address: int) -> dict[str, Any]:
        path = Path(image).expanduser().resolve()
        if not path.is_file():
            raise MCPError(f"Image does not exist: {path}", "IMAGE_NOT_FOUND")
        out = self.execute(["connect", f'verifybin "{path}" 0x{address:X}'], 900)
        return {"verified": True, "image": str(path), "address": f"0x{address:X}", "output": tail(out)}

    def erase(self, start: int | None = None, end: int | None = None) -> dict[str, Any]:
        command = "erase"
        if start is not None and end is not None:
            command += f" 0x{start:X} 0x{end:X}"
        return {"output": tail(self.execute(["connect", command], 900))}

    def raw(self, command: str) -> str:
        return self.execute(["connect", command], 120)

    def list_probes(self) -> dict[str, Any]:
        result = self.runner.run(self.cfg.executables.jlink, ["-ListUSB"], timeout=20)
        return {"returncode": result.returncode, "output": tail(result.output, 8000)}


def tail(text: str, limit: int = 4000) -> str:
    return text[-limit:]


def parse_mem8(output: str, expected: int) -> bytes:
    """Parse J-Link Mem8 output without accidentally consuming ASCII columns.

    J-Link's output formatting varies by software version. We only accept byte tokens from
    the hexadecimal data portion of lines that begin with an address, which avoids parsing
    the printable ASCII column as data.
    """
    result = bytearray()
    address_line = re.compile(r"^\s*([0-9A-Fa-f]{8,16})\s+(.+)$")
    for line in output.splitlines():
        match = address_line.match(line)
        if not match:
            continue
        payload = match.group(2)
        # Stop at a common ASCII separator if present.
        payload = re.split(r"\s{2,}[|]", payload, maxsplit=1)[0]
        tokens = re.findall(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{2}(?![0-9A-Fa-f])", payload)
        result.extend(int(token, 16) for token in tokens)
        if len(result) >= expected:
            break
    return bytes(result[:expected])
