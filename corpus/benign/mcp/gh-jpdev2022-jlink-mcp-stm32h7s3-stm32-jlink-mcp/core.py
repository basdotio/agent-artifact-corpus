from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Target(BaseModel):
    device: str = "STM32H7S3L8"
    interface: str = "SWD"
    speed_khz: int = 4000
    jlink_serial: int | None = None


class Executables(BaseModel):
    jlink: str = "JLinkExe"
    gdb_server: str = "JLinkGDBServer"
    gdb: str = "arm-none-eabi-gdb"


class ExternalFlash(BaseModel):
    enabled: bool = True
    controller: str = "XSPI2"
    mapped_address: int = 0x70000000
    size: int = 0
    jedec_id: str | None = None


class Debug(BaseModel):
    gdb_port: int = 2331
    gdb_startup_timeout_s: float = 8
    gdb_command_timeout_s: float = 5


class Safety(BaseModel):
    require_erase_confirmation: bool = True
    max_memory_write_bytes: int = 4096
    allow_raw_jlink_command: bool = True


class Config(BaseModel):
    target: Target = Field(default_factory=Target)
    executables: Executables = Field(default_factory=Executables)
    external_flash: ExternalFlash = Field(default_factory=ExternalFlash)
    debug: Debug = Field(default_factory=Debug)
    safety: Safety = Field(default_factory=Safety)


def load_config() -> Config:
    path = os.environ.get("STM32_JLINK_MCP_CONFIG", "config.yaml")
    p = Path(path)
    if not p.exists():
        return Config()
    return Config.model_validate(yaml.safe_load(p.read_text()) or {})


class MCPError(Exception):
    def __init__(self, message: str, code: str = "ERROR"):
        super().__init__(message)
        self.code = code


class Runner:
    def resolve(self, executable: str) -> str:
        if os.path.isabs(executable) and os.path.exists(executable):
            return executable
        value = shutil.which(executable)
        if value:
            return value
        raise MCPError(f"Executable not found: {executable}", "EXECUTABLE_NOT_FOUND")

    def run(self, executable: str, args: list[str], stdin: str | None = None,
            timeout: float = 60) -> subprocess.CompletedProcess[str]:
        exe = self.resolve(executable)
        try:
            return subprocess.run(
                [exe, *args],
                input=stdin,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise MCPError(f"Command timed out: {exe}", "COMMAND_TIMEOUT") from exc


class JLink:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.runner = Runner()

    def _run(self, commands: list[str], timeout: float = 60) -> str:
        t = self.cfg.target
        args = [
            "-device", t.device,
            "-if", t.interface,
            "-speed", str(t.speed_khz),
        ]
        if t.jlink_serial is not None:
            args += ["-SelectEmuBySN", str(t.jlink_serial)]
        script = "\n".join(commands + ["exit"]) + "\n"
        result = self.runner.run(self.cfg.executables.jlink, args, script, timeout)
        output = (result.stdout + "\n" + result.stderr).strip()
        if result.returncode != 0:
            raise MCPError(output or "J-Link command failed", "JLINK_FAILED")
        return output

    def connect(self) -> dict[str, Any]:
        out = self._run(["connect"], 20)
        return {"connected": True, "output": out[-4000:]}

    def status(self) -> dict[str, Any]:
        out = self._run(["connect", "regs"], 20)
        return {"connected": True, "output": out[-8000:]}

    def reset(self) -> dict[str, Any]:
        return {"output": self._run(["connect", "reset", "go"], 20)[-3000:]}

    def halt(self) -> dict[str, Any]:
        return {"output": self._run(["connect", "halt"], 20)[-3000:]}

    def run(self) -> dict[str, Any]:
        return {"output": self._run(["connect", "go"], 20)[-3000:]}

    def step(self) -> dict[str, Any]:
        return {"output": self._run(["connect", "halt", "step", "regs"], 20)[-5000:]}

    def registers(self) -> dict[str, Any]:
        return {"output": self._run(["connect", "regs"], 20)[-8000:]}

    def read_memory(self, address: int, length: int) -> dict[str, Any]:
        if length <= 0:
            raise MCPError("length must be positive", "INVALID_ARGUMENT")
        out = self._run(["connect", f"mem8 0x{address:X}, {length}"], 30)
        data = parse_mem8(out, length)
        return {
            "address": f"0x{address:08X}",
            "length": length,
            "data_hex": data.hex(),
            "output": out[-3000:],
        }

    def write_memory(self, address: int, data: bytes) -> dict[str, Any]:
        commands = ["connect"]
        for off in range(0, len(data), 4):
            chunk = data[off:off + 4].ljust(4, b"\0")
            value = int.from_bytes(chunk, "little")
            commands.append(f"w4 0x{address + off:X}, 0x{value:08X}")
        out = self._run(commands, 30)
        return {"address": f"0x{address:08X}", "length": len(data), "output": out[-4000:]}

    def program(self, image: str, address: int | None) -> dict[str, Any]:
        p = Path(image).expanduser().resolve()
        if not p.is_file():
            raise MCPError(f"Image does not exist: {p}", "IMAGE_NOT_FOUND")
        cmd = f"loadfile {p}"
        if address is not None:
            cmd += f" 0x{address:X}"
        out = self._run(["connect", cmd], 600)
        return {"image": str(p), "address": address, "output": out[-8000:]}

    def verify(self, image: str, address: int) -> dict[str, Any]:
        p = Path(image).expanduser().resolve()
        if not p.is_file():
            raise MCPError(f"Image does not exist: {p}", "IMAGE_NOT_FOUND")
        out = self._run(["connect", f"verifybin {p} 0x{address:X}"], 600)
        return {"verified": True, "image": str(p), "address": f"0x{address:X}", "output": out[-6000:]}

    def erase(self) -> dict[str, Any]:
        return {"output": self._run(["connect", "erase"], 600)[-6000:]}

    def raw(self, command: str) -> str:
        return self._run(["connect", command], 60)


def parse_mem8(output: str, expected: int) -> bytes:
    result: list[int] = []
    for line in output.splitlines():
        if ":" not in line:
            continue
        payload = line.split(":", 1)[1]
        tokens = re.findall(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{2}(?![0-9A-Fa-f])", payload)
        result.extend(int(t, 16) for t in tokens)
        if len(result) >= expected:
            break
    return bytes(result[:expected])


class ElfSymbols:
    def __init__(self):
        self.symbols: dict[str, int] = {}

    def load(self, path: str) -> dict[str, Any]:
        from elftools.elf.elffile import ELFFile
        p = Path(path).expanduser().resolve()
        with p.open("rb") as f:
            elf = ELFFile(f)
            for section_name in (".symtab", ".dynsym"):
                section = elf.get_section_by_name(section_name)
                if not section:
                    continue
                for sym in section.iter_symbols():
                    if sym.name and sym["st_value"]:
                        self.symbols.setdefault(sym.name, int(sym["st_value"]))
        return {"loaded": True, "path": str(p), "symbols": len(self.symbols)}

    def symbol(self, name: str) -> dict[str, Any]:
        value = self.symbols.get(name)
        if value is None:
            return {"found": False, "symbol": name}
        return {"found": True, "symbol": name, "address": f"0x{value:08X}"}

    def address(self, address: int) -> dict[str, Any]:
        candidates = [(v, n) for n, v in self.symbols.items() if v <= address]
        if not candidates:
            return {"found": False, "address": f"0x{address:08X}"}
        value, name = max(candidates)
        return {
            "found": True,
            "address": f"0x{address:08X}",
            "symbol": name,
            "symbol_address": f"0x{value:08X}",
            "offset": address - value,
        }
