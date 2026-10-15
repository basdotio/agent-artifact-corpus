from __future__ import annotations

from typing import Any

from .config import Config
from .diagnostics.cortex_m import read_fault_info
from .errors import MCPError
from .gdb.session import GdbSession
from .probe.jlink import JLinkBackend
from .rtt import RttSession
from .safety.policy import SafetyPolicy
from .session import DebugSession
from .svd.parser import SvdDatabase
from .symbols import ElfSymbols
from .targets import STM32H7S3_PROFILE


class DebugService:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.jlink = JLinkBackend(cfg)
        self.session = DebugSession(cfg, self.jlink)
        self.gdb = GdbSession(cfg, self.jlink.runner)
        self.safety = SafetyPolicy(cfg)
        self.rtt = RttSession(cfg)
        self.symbols = ElfSymbols()
        self.svd = SvdDatabase()
        self.profile = STM32H7S3_PROFILE
        if cfg.svd.path:
            self.svd.load(cfg.svd.path)
        if cfg.elf.path:
            self.symbols.load(cfg.elf.path)

    def connect(self) -> dict[str, Any]:
        with self.session.operation():
            result = self.jlink.connect()
            self.session.mark_connected()
            return {**result, "state": self.session.state.value}

    def disconnect(self) -> dict[str, Any]:
        with self.session.operation():
            self.rtt.stop_host()
            self.session.mark_disconnected()
            return {"disconnected": True}

    def status(self) -> dict[str, Any]:
        with self.session.operation():
            result = self.jlink.status()
            self.session.mark_connected()
            return {
                **result,
                "state": self.session.state.value,
                "gdb_active": self.session.gdb_active,
                "profile": self.profile.name,
                "rtt": self.rtt.status(),
            }

    def identify(self) -> dict[str, Any]:
        with self.session.operation():
            return self.jlink.identify()

    def halt(self) -> dict[str, Any]:
        with self.session.operation():
            result = self.jlink.halt()
            self.session.mark_halted()
            return {**result, "state": self.session.state.value}

    def run(self) -> dict[str, Any]:
        with self.session.operation():
            result = self.jlink.run()
            self.session.mark_running()
            return {**result, "state": self.session.state.value}

    def reset(self, run_after: bool = True) -> dict[str, Any]:
        with self.session.operation():
            result = self.jlink.reset(run_after=run_after)
            self.session.mark_running() if run_after else self.session.mark_halted()
            return {**result, "state": self.session.state.value}

    def step(self) -> dict[str, Any]:
        with self.session.operation():
            result = self.jlink.step()
            self.session.mark_halted()
            return {**result, "state": self.session.state.value}

    def read_memory(self, address: int, length: int) -> dict[str, Any]:
        self.safety.check_read_length(length)
        with self.session.operation():
            return self.jlink.read_memory(address, length)

    def write_memory(self, address: int, data_hex: str, confirmation: str = "") -> dict[str, Any]:
        self.safety.require_read_write_mode("memory_write")
        try:
            data = bytes.fromhex(data_hex)
        except ValueError as exc:
            raise MCPError("data_hex is not valid hexadecimal", "INVALID_ARGUMENT") from exc
        self.safety.check_write_length(len(data))
        region = self.profile.region_for(address, len(data))
        if region is not None and not region.writable:
            raise MCPError(
                f"Memory region {region.name} is not a generic writable region",
                "MEMORY_REGION_READ_ONLY",
            )
        if self.cfg.safety.require_write_confirmation:
            self.safety.require_confirmation(confirmation, "WRITE_MEMORY")
        with self.session.operation():
            return self.jlink.write_memory(address, data)

    def register_write(self, peripheral: str, register: str, value: int, confirmation: str = "") -> dict[str, Any]:
        self.safety.require_read_write_mode("register_write")
        if self.cfg.safety.require_write_confirmation:
            self.safety.require_confirmation(confirmation, "WRITE_REGISTER")
        info = self.svd.register_info(peripheral, register)
        access = info["access"].lower()
        if "write" not in access:
            raise MCPError(f"Register is not writable: {peripheral}.{register}", "REGISTER_READ_ONLY")
        width = info["size_bits"]
        if width not in (8, 16, 32):
            raise MCPError("Only 8/16/32-bit SVD registers are supported", "SVD_UNSUPPORTED_WIDTH")
        max_value = (1 << width) - 1
        if value < 0 or value > max_value:
            raise MCPError("register value exceeds the register width", "INVALID_ARGUMENT")
        with self.session.operation():
            # J-Link register writes are core-register oriented; for peripheral registers use
            # target memory writes so the SVD address is explicit and auditable.
            address = int(info["address"], 16)
            data = value.to_bytes(width // 8, "little")
            return self.jlink.write_memory(address, data)

    def program_internal(self, image: str, address: int | None, confirmation: str = "") -> dict[str, Any]:
        self.safety.require_read_write_mode("flash_program")
        if self.cfg.safety.require_flash_confirmation:
            self.safety.require_confirmation(confirmation, "PROGRAM_INTERNAL_FLASH")
        with self.session.operation():
            return self.jlink.program(image, address)

    def verify_bin(self, image: str, address: int) -> dict[str, Any]:
        with self.session.operation():
            return self.jlink.verify_bin(image, address)

    def erase_internal(self, confirmation: str) -> dict[str, Any]:
        self.safety.require_read_write_mode("flash_erase")
        if self.cfg.safety.require_flash_confirmation:
            self.safety.require_confirmation(confirmation, "ERASE_INTERNAL_FLASH")
        with self.session.operation():
            return self.jlink.erase()

    def start_gdb(self, elf: str | None = None) -> dict[str, Any]:
        self.session.acquire_gdb()
        try:
            result = self.gdb.start(elf)
            self.session.mark_connected()
            return {**result, "gdb_active": True}
        except Exception:
            self.session.release_gdb()
            self.gdb.stop()
            raise

    def stop_gdb(self) -> dict[str, Any]:
        self.gdb.stop()
        self.session.release_gdb()
        return {"stopped": True, "gdb_active": False}

    def gdb_command(self, command: str) -> list[dict[str, Any]]:
        with self.session.operation(allow_with_gdb=True):
            return self.gdb.command(command)

    def fault_info_from_gdb(self) -> dict[str, Any]:
        if not self.session.gdb_active:
            return self.fault_info()
        # GDB owns the target during a debug session, so read fault registers through GDB/MI
        # instead of opening a competing J-Link Commander connection.
        values: dict[str, int | None] = {}
        addresses = {
            "ICSR": 0xE000ED04, "SHCSR": 0xE000ED24, "CFSR": 0xE000ED28,
            "HFSR": 0xE000ED2C, "DFSR": 0xE000ED30, "MMFAR": 0xE000ED34,
            "BFAR": 0xE000ED38, "AFSR": 0xE000ED3C,
        }
        for name, address in addresses.items():
            responses = self.gdb_command(f'-data-read-memory-bytes 0x{address:X} 4')
            value = None
            for response in responses:
                payload = response.get("payload") if isinstance(response, dict) else None
                if isinstance(payload, dict):
                    memory = payload.get("memory", [])
                    if memory and isinstance(memory[0], dict):
                        contents = memory[0].get("contents", "")
                        if len(contents) >= 8:
                            value = int.from_bytes(bytes.fromhex(contents[:8]), "little")
                            break
            values[name] = value
        cfsr = values.get("CFSR") or 0
        hfsr = values.get("HFSR") or 0
        return {
            "registers": {k: f"0x{v:08X}" if v is not None else None for k, v in values.items()},
            "decoded": {
                "memmanage_fault": bool(cfsr & 0x000000FF),
                "bus_fault": bool(cfsr & 0x0000FF00),
                "usage_fault": bool(cfsr & 0xFFFF0000),
                "hard_fault_forced": bool(hfsr & (1 << 30)),
                "hard_fault_debug_event": bool(hfsr & (1 << 31)),
                "memmanage_mmar_valid": bool(cfsr & (1 << 7)),
                "busfault_bfar_valid": bool(cfsr & (1 << 15)),
                "busfault_precise": bool(cfsr & (1 << 9)),
                "busfault_imprecise": bool(cfsr & (1 << 10)),
                "usage_divide_by_zero": bool(cfsr & (1 << 25)),
                "usage_unaligned": bool(cfsr & (1 << 24)),
            },
            "source": "gdb",
        }

    def fault_info(self) -> dict[str, Any]:
        with self.session.operation():
            return read_fault_info(self.jlink)

    def snapshot(self) -> dict[str, Any]:
        with self.session.operation():
            return {
                "target": self.jlink.status(),
                "fault": read_fault_info(self.jlink),
                "profile": self.profile.name,
                "external_flash": self.external_flash_info(),
                "symbols_loaded": self.symbols.path,
                "svd": self.svd.info(),
            }

    def reset_reason(self) -> dict[str, Any]:
        # Do not hard-code an RCC address across STM32 families/revisions. When the official
        # device SVD is loaded, resolve RCC.RSR from the SVD and read it without clearing flags.
        if not self.svd.path:
            return {
                "available": False,
                "reason": "Load the official STM32H7S3 CMSIS-SVD so RCC.RSR can be resolved for the exact device definition.",
            }
        info = self.svd.register_info("RCC", "RSR")
        raw = self.read_memory(int(info["address"], 16), max(1, info["size_bits"] // 8))
        value = int.from_bytes(bytes.fromhex(raw["data_hex"]), "little")
        fields = {}
        for field in info["fields"]:
            if field["bit_width"]:
                mask = (1 << field["bit_width"]) - 1
                fields[field["name"]] = (value >> field["bit_offset"]) & mask
        return {
            "available": True,
            "register": info,
            "value": f"0x{value:08X}",
            "fields": fields,
            "cleared": False,
            "note": "Reset flags are read-only status evidence here; this tool does not clear them.",
        }

    def external_flash_info(self) -> dict[str, Any]:
        e = self.cfg.external_flash
        return {
            "enabled": e.enabled,
            "controller": e.controller,
            "mapped_address": f"0x{e.mapped_address:08X}",
            "size_bytes": e.size,
            "size_mib": e.size / (1024 * 1024),
            "part_number": e.part_number,
            "density_bits": e.density_bits,
            "voltage": {"min_v": e.voltage_min_v, "max_v": e.voltage_max_v},
            "max_clock_mhz": e.max_clock_mhz,
            "protocol": e.protocol,
            "chip_select": e.chip_select,
            "expected_jedec_id": e.jedec_id,
            "hal_memory_size": e.hal_memory_size,
            "program_enabled": False,
            "erase_enabled": False,
            "identity_source": "configuration",
            "warning": (
                "Configured board identity only; this does not prove the NOR is initialized, "
                "memory-mapped, or responding. A future XSPI indirect-mode probe should "
                "compare the live RDID/SFDP evidence with this configuration."
            ),
        }

    def external_flash_read(self, offset: int, length: int) -> dict[str, Any]:
        e = self.cfg.external_flash
        if not e.enabled:
            raise MCPError("External flash support is disabled", "EXTERNAL_FLASH_DISABLED")
        if offset < 0 or length <= 0:
            raise MCPError("offset must be >= 0 and length must be > 0", "INVALID_ARGUMENT")
        if e.size and offset + length > e.size:
            raise MCPError("external flash read exceeds configured size", "ADDRESS_RANGE")
        self.safety.check_read_length(length)
        return self.read_memory(e.mapped_address + offset, length)

    def external_flash_test(self) -> dict[str, Any]:
        e = self.cfg.external_flash
        sample = self.external_flash_read(0, min(16, self.cfg.safety.max_memory_read_bytes))
        return {
            "controller": e.controller,
            "mapped_address": f"0x{e.mapped_address:08X}",
            "read_test": "PASS",
            "sample": sample,
            "caveat": "A successful CPU read proves accessibility of the mapped window, not NOR identity or programming support.",
        }

    def external_flash_program(self, image: str, address: int, confirmation: str) -> dict[str, Any]:
        raise MCPError(
            "External NOR programming is intentionally not implemented generically. "
            "Add a board/flash-specific programmer backend and loader after validating the exact NOR part and XSPI configuration.",
            "EXTERNAL_FLASH_PROGRAM_UNIMPLEMENTED",
            recoverable=False,
        )

    def external_flash_erase(self, start: int, end: int, confirmation: str) -> dict[str, Any]:
        raise MCPError(
            "External NOR erase is intentionally not implemented generically. "
            "J-Link's device flash erase algorithm must not be assumed to erase an arbitrary memory-mapped NOR.",
            "EXTERNAL_FLASH_ERASE_UNIMPLEMENTED",
            recoverable=False,
        )

    def rtt_connect(self) -> dict[str, Any]:
        if not self.cfg.rtt.enabled:
            raise MCPError("RTT support is disabled", "RTT_DISABLED")
        with self.session.operation(allow_with_gdb=True):
            if self.gdb.gdb is None:
                # RTT requires a live J-Link debug connection. Start the same GDB Server
                # transport used by the debugger, but do not create a GDB client. This
                # keeps the probe connection alive while the RTT TELNET channel is used.
                self._start_rtt_host()
            return self.rtt.attach_socket(
                self.cfg.rtt.host,
                self.cfg.rtt.telnet_port,
                self.cfg.rtt.connect_timeout_s,
            )

    def _start_rtt_host(self) -> None:
        import socket
        import subprocess
        import time

        if self.rtt.host_owned:
            return
        server_exe = self.jlink.runner.resolve(self.cfg.executables.gdb_server)
        args = [
            server_exe,
            "-device", self.cfg.target.jlink_device,
            "-if", self.cfg.target.interface,
            "-speed", str(self.cfg.target.speed_khz),
            "-port", str(self.cfg.debug.gdb_port + 1),
            "-RTTTelnetPort", str(self.cfg.rtt.telnet_port),
            "-localhostonly", "1",
            "-silent",
            "-noreset",
            "-nohalt",
            "-nosinglerun",
        ]
        if self.cfg.target.jlink_serial is not None:
            args += ["-USB", str(self.cfg.target.jlink_serial)]
        proc = subprocess.Popen(
            args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        deadline = time.monotonic() + self.cfg.debug.gdb_startup_timeout_s
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                output = proc.stdout.read() if proc.stdout else ""
                raise MCPError(
                    f"J-Link GDB Server RTT host exited: {output[-2000:]}",
                    "RTT_HOST_FAILED",
                )
            try:
                with socket.create_connection((self.cfg.rtt.host, self.cfg.rtt.telnet_port), timeout=0.2):
                    self.rtt.set_host_process(proc, True)
                    return
            except OSError:
                time.sleep(self.cfg.debug.gdb_poll_interval_s)
        if proc.poll() is None:
            proc.terminate()
        raise MCPError("Timed out waiting for J-Link RTT TELNET port", "RTT_HOST_TIMEOUT")

    def rtt_read(self, max_bytes: int = 4096) -> dict[str, Any]:
        with self.session.operation(allow_with_gdb=True):
            return self.rtt.read(max_bytes, self.cfg.rtt.read_timeout_s)

    def rtt_write(self, data_hex: str) -> dict[str, Any]:
        try:
            data = bytes.fromhex(data_hex)
        except ValueError as exc:
            raise MCPError("data_hex must contain an even number of hexadecimal digits", "INVALID_ARGUMENT") from exc
        with self.session.operation(allow_with_gdb=True):
            return self.rtt.write(data)

    def rtt_disconnect(self) -> dict[str, Any]:
        with self.session.operation(allow_with_gdb=True):
            self.rtt.stop_host()
            return {"disconnected": True}

    def nrst_assert(self) -> dict[str, Any]:
        with self.session.operation():
            return {"output": self.jlink.raw("r0")}

    def nrst_release(self) -> dict[str, Any]:
        with self.session.operation():
            return {"output": self.jlink.raw("r1")}

    def nrst_pulse(self, assert_ms: int = 50, release_wait_ms: int = 100) -> dict[str, Any]:
        if assert_ms < 1 or release_wait_ms < 0:
            raise MCPError("assert_ms must be >= 1 and release_wait_ms must be >= 0", "INVALID_ARGUMENT")
        import time
        with self.session.operation():
            self.jlink.raw("r0")
            time.sleep(assert_ms / 1000.0)
            self.jlink.raw("r1")
            time.sleep(release_wait_ms / 1000.0)
            return {"assert_ms": assert_ms, "release_wait_ms": release_wait_ms, "nrst": "released"}

    def program_verify_rtt_nrst(
        self, image: str, address: int | None, erase_confirmation: str, program_confirmation: str,
        verify_address: int | None = None, assert_ms: int = 50, release_wait_ms: int = 100,
    ) -> dict[str, Any]:
        # Deliberately keep the sequence explicit and auditable: erase -> program -> verify ->
        # establish RTT transport -> hardware NRST pulse. RTT must be established before the
        # reset release so application boot logs can be captured.
        erase = self.erase_internal(erase_confirmation)
        program = self.program_internal(image, address, program_confirmation)
        if verify_address is None:
            verify_address = address
        if verify_address is None:
            raise MCPError("verify_address is required for a binary image", "INVALID_ARGUMENT")
        verify = self.verify_bin(image, verify_address)
        rtt = self.rtt_connect()
        nrst = self.nrst_pulse(assert_ms, release_wait_ms)
        return {"sequence": ["erase", "program", "verify", "rtt_connect", "nrst_pulse"], "erase": erase, "program": program, "verify": verify, "rtt": rtt, "nrst": nrst}

    def load_symbols(self, elf: str) -> dict[str, Any]:
        result = self.symbols.load(elf)
        if self.gdb.gdb is not None:
            self.gdb.load_elf(elf)
        return result
