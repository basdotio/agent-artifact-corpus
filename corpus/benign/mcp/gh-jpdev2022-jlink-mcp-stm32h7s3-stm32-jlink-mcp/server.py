from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .errors import MCPError
from .service import DebugService

cfg = load_config()
service = DebugService(cfg)

mcp = FastMCP(
    "stm32-jlink-mcp",
    instructions=(
        "Stateful semantic STM32H7S3 debugging through SEGGER J-Link. "
        "Prefer semantic tools over raw J-Link commands. "
        "Do not assume external XSPI/NOR configuration from address windows alone. "
        "Destructive operations require explicit confirmation tokens."
    ),
)


def call(operation: str, fn) -> dict[str, Any]:
    try:
        return {"success": True, "operation": operation, "data": fn()}
    except MCPError as exc:
        return {
            "success": False,
            "operation": operation,
            "error": {
                "code": exc.code,
                "message": str(exc),
                "recoverable": exc.recoverable,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive boundary for MCP process
        return {
            "success": False,
            "operation": operation,
            "error": {"code": "UNEXPECTED_ERROR", "message": str(exc), "recoverable": False},
        }


@mcp.tool()
def probe_list():
    """List J-Link probes visible to the host."""
    return call("probe_list", service.jlink.list_probes)


@mcp.tool()
def jlink_connect():
    """Connect to the configured STM32 target and establish a managed low-level session."""
    return call("jlink_connect", service.connect)


@mcp.tool()
def jlink_disconnect():
    """Release the logical target connection managed by this MCP server."""
    return call("jlink_disconnect", service.disconnect)


@mcp.tool()
def jlink_status():
    """Return J-Link target evidence and current session ownership/state."""
    return call("jlink_status", service.status)


@mcp.tool()
def target_identify():
    """Identify the configured target connection; use before destructive operations."""
    return call("target_identify", service.identify)


@mcp.tool()
def target_reset(run_after: bool = True):
    """Reset the target; optionally leave it halted instead of resuming."""
    return call("target_reset", lambda: service.reset(run_after))


@mcp.tool()
def target_halt():
    """Halt the target CPU."""
    return call("target_halt", service.halt)


@mcp.tool()
def target_run():
    """Resume target execution."""
    return call("target_run", service.run)


@mcp.tool()
def target_step():
    """Single-step the target using J-Link Commander."""
    return call("target_step", service.step)


@mcp.tool()
def target_status():
    """Return target registers, connection state, and GDB ownership."""
    return call("target_status", service.status)


@mcp.tool()
def memory_read(address: int, length: int):
    """Read target memory as bytes."""
    return call("memory_read", lambda: service.read_memory(address, length))


@mcp.tool()
def memory_write(address: int, data_hex: str, confirmation: str = ""):
    """Write target memory. Exact confirmation WRITE_MEMORY is required by default."""
    return call("memory_write", lambda: service.write_memory(address, data_hex, confirmation))


@mcp.tool()
def registers_read():
    """Read Cortex-M core registers through J-Link."""
    return call("registers_read", lambda: service.status()["register_output"])


@mcp.tool()
def register_read(peripheral: str, register: str):
    """Read an SVD-described peripheral register, including decoded field values."""
    def op():
        info = service.svd.register_info(peripheral, register)
        raw = service.read_memory(int(info["address"], 16), max(1, info["size_bits"] // 8))
        value = int.from_bytes(bytes.fromhex(raw["data_hex"]), "little")
        fields = {}
        for field in info["fields"]:
            mask = (1 << field["bit_width"]) - 1 if field["bit_width"] else 0
            fields[field["name"]] = (value >> field["bit_offset"]) & mask
        return {**info, "value": f"0x{value:X}", "fields_decoded": fields}
    return call("register_read", op)


@mcp.tool()
def register_write(peripheral: str, register: str, value: int, confirmation: str = ""):
    """Write an SVD-described peripheral register; exact WRITE_REGISTER confirmation is required by default."""
    return call("register_write", lambda: service.register_write(peripheral, register, value, confirmation))


@mcp.tool()
def flash_program(image: str, address: int | None = None, confirmation: str = ""):
    """Program internal/device flash using SEGGER LoadFile; exact PROGRAM_INTERNAL_FLASH confirmation is required by default."""
    return call("flash_program", lambda: service.program_internal(image, address, confirmation))


@mcp.tool()
def flash_verify(image: str, address: int):
    """Verify a binary image against target memory using SEGGER VerifyBin."""
    return call("flash_verify", lambda: service.verify_bin(image, address))


@mcp.tool()
def flash_erase(confirmation: str = ""):
    """Erase device flash. Exact ERASE_INTERNAL_FLASH confirmation is required by default."""
    return call("flash_erase", lambda: service.erase_internal(confirmation))


@mcp.tool()
def debug_start(elf: str | None = None):
    """Start a managed J-Link GDB Server and GDB/MI session."""
    return call("debug_start", lambda: service.start_gdb(elf))


@mcp.tool()
def debug_stop():
    """Stop the managed GDB and J-Link GDB Server session."""
    return call("debug_stop", service.stop_gdb)


@mcp.tool()
def debug_continue():
    """Continue target execution through GDB."""
    return call("debug_continue", lambda: {"responses": service.gdb_command("-exec-continue")})


@mcp.tool()
def debug_pause():
    """Interrupt target execution through GDB."""
    return call("debug_pause", lambda: {"responses": service.gdb_command("-exec-interrupt")})


@mcp.tool()
def debug_step():
    """Single-step the current frame through GDB."""
    return call("debug_step", lambda: {"responses": service.gdb_command("-exec-step")})


@mcp.tool()
def debug_breakpoint_set(location: str):
    """Set a breakpoint by symbol, source location, or address."""
    return call("debug_breakpoint_set", lambda: {"responses": service.gdb_command(f'-break-insert "{location}"')})


@mcp.tool()
def debug_breakpoint_clear(number: str):
    """Clear a GDB breakpoint number."""
    return call("debug_breakpoint_clear", lambda: {"responses": service.gdb_command(f"-break-delete {number}")})


@mcp.tool()
def debug_watchpoint_set(expression: str, access: str = "write"):
    """Set a GDB watchpoint. Access is read, access, or write."""
    access_map = {"read": "-break-watch", "write": "-break-watch", "access": "-break-watch"}
    if access not in access_map:
        return call("debug_watchpoint_set", lambda: (_ for _ in ()).throw(MCPError("access must be read, write, or access", "INVALID_ARGUMENT")))
    command = f'-break-watch "{expression}"'
    if access == "read":
        command = f'-break-watch -r "{expression}"'
    elif access == "access":
        command = f'-break-watch -a "{expression}"'
    return call("debug_watchpoint_set", lambda: {"responses": service.gdb_command(command)})


@mcp.tool()
def debug_watchpoint_clear(number: str):
    """Clear a GDB watchpoint number."""
    return call("debug_watchpoint_clear", lambda: {"responses": service.gdb_command(f"-break-delete {number}")})


@mcp.tool()
def debug_stop_reason():
    """Return the current GDB execution/stop record."""
    return call("debug_stop_reason", lambda: {"responses": service.gdb_command("-thread-info")})


@mcp.tool()
def debug_backtrace():
    """Return the current GDB stack frames."""
    return call("debug_backtrace", lambda: {"responses": service.gdb_command("-stack-list-frames")})


@mcp.tool()
def read_variable(name: str):
    """Evaluate a runtime GDB expression/variable."""
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return call("read_variable", lambda: {"responses": service.gdb_command(f'-data-evaluate-expression "{escaped}"')})


@mcp.tool()
def rtt_connect():
    """Connect to J-Link RTT channel 0. Starts a persistent J-Link debug transport if needed."""
    return call("rtt_connect", service.rtt_connect)


@mcp.tool()
def rtt_read(max_bytes: int = 4096):
    """Read available bytes from RTT channel 0; a timeout returns zero bytes."""
    return call("rtt_read", lambda: service.rtt_read(max_bytes))


@mcp.tool()
def rtt_write(data_hex: str):
    """Write hexadecimal bytes to RTT down channel 0."""
    return call("rtt_write", lambda: service.rtt_write(data_hex))


@mcp.tool()
def rtt_disconnect():
    """Disconnect RTT and stop its dedicated J-Link transport when MCP owns it."""
    return call("rtt_disconnect", service.rtt_disconnect)


@mcp.tool()
def nrst_assert():
    """Assert the J-Link-controlled NRST pin (J-Link RESET pin)."""
    return call("nrst_assert", service.nrst_assert)


@mcp.tool()
def nrst_release():
    """Release the J-Link-controlled NRST pin."""
    return call("nrst_release", service.nrst_release)


@mcp.tool()
def nrst_pulse(assert_ms: int = 50, release_wait_ms: int = 100):
    """Assert NRST for assert_ms, release it, then wait release_wait_ms."""
    return call("nrst_pulse", lambda: service.nrst_pulse(assert_ms, release_wait_ms))


@mcp.tool()
def program_verify_rtt_nrst(
    image: str,
    address: int | None = None,
    erase_confirmation: str = "",
    program_confirmation: str = "",
    verify_address: int | None = None,
    assert_ms: int = 50,
    release_wait_ms: int = 100,
):
    """Run the preferred deployment sequence: erase -> program -> verify -> RTT connect -> NRST pulse."""
    return call(
        "program_verify_rtt_nrst",
        lambda: service.program_verify_rtt_nrst(
            image, address, erase_confirmation, program_confirmation, verify_address, assert_ms, release_wait_ms
        ),
    )


@mcp.tool()
def load_symbols(elf: str):
    """Load ELF symbols and, if GDB is active, load the same ELF into GDB."""
    return call("load_symbols", lambda: service.load_symbols(elf))


@mcp.tool()
def resolve_symbol(name: str):
    """Resolve a loaded ELF symbol to its address."""
    return call("resolve_symbol", lambda: service.symbols.symbol(name))


@mcp.tool()
def resolve_address(address: int):
    """Resolve an address to the nearest loaded ELF symbol."""
    return call("resolve_address", lambda: service.symbols.address(address))


@mcp.tool()
def svd_info():
    """Return loaded SVD metadata."""
    return call("svd_info", service.svd.info)


@mcp.tool()
def peripheral_info(peripheral: str):
    """Describe an SVD peripheral and list its registers."""
    return call("peripheral_info", lambda: service.svd.peripheral_info(peripheral))


@mcp.tool()
def register_info(peripheral: str, register: str):
    """Describe an SVD register, including address and fields."""
    return call("register_info", lambda: service.svd.register_info(peripheral, register))


@mcp.tool()
def stm32_fault_info():
    """Read and decode Cortex-M fault status evidence."""
    return call("stm32_fault_info", service.fault_info)


@mcp.tool()
def stm32_snapshot():
    """Collect a compact target/GDB/fault/SVD/XSPI evidence snapshot."""
    return call("stm32_snapshot", service.snapshot)


@mcp.tool()
def stm32_reset_reason():
    """Read RCC reset-status evidence from the loaded official SVD without clearing flags."""
    return call("stm32_reset_reason", service.reset_reason)


@mcp.tool()
def boot_diagnose():
    """Collect evidence useful for boot failures without claiming undocumented boot-ROM behavior."""
    return call("boot_diagnose", service.snapshot)


@mcp.tool()
def external_flash_info():
    """Return configured XSPI/NOR policy and address window; does not probe hardware."""
    return call("external_flash_info", service.external_flash_info)


@mcp.tool()
def external_flash_read(offset: int = 0, length: int = 64):
    """Read a configured memory-mapped external NOR window after firmware initialized XSPI."""
    return call("external_flash_read", lambda: service.external_flash_read(offset, length))


@mcp.tool()
def external_flash_test():
    """Perform a small non-destructive CPU read from the configured external-memory window."""
    return call("external_flash_test", service.external_flash_test)


@mcp.tool()
def external_flash_program(image: str, address: int, confirmation: str = ""):
    """Program external flash only when an explicitly validated board-specific loader is enabled."""
    return call("external_flash_program", lambda: service.external_flash_program(image, address, confirmation))


@mcp.tool()
def external_flash_erase(start: int, end: int, confirmation: str = ""):
    """Erase external flash only when explicitly enabled for the validated board/loader."""
    return call("external_flash_erase", lambda: service.external_flash_erase(start, end, confirmation))


@mcp.tool()
def flash_and_verify(image: str, address: int, confirmation: str = ""):
    """Program an image and then verify a binary at the same address."""
    def op():
        if not image.lower().endswith(".bin"):
            raise MCPError("flash_and_verify requires a .bin image because VerifyBin is binary-only", "INVALID_ARGUMENT")
        service.program_internal(image, address, confirmation)
        return service.verify_bin(image, address)
    return call("flash_and_verify", op)


@mcp.tool()
def diagnose_crash():
    """Capture fault state, target state, and debug backtrace when GDB is active."""
    def op():
        if service.session.gdb_active:
            return {
                "target": {"gdb_active": True},
                "fault": service.fault_info_from_gdb(),
                "backtrace": service.gdb_command("-stack-list-frames"),
                "stop_reason": service.gdb_command("-thread-info"),
            }
        return service.snapshot()
    return call("diagnose_crash", op)


@mcp.tool()
def jlink_command(command: str):
    """Expert escape hatch for one raw J-Link Commander command; disabled by default."""
    def op():
        if not cfg.safety.allow_raw_jlink_command:
            raise MCPError("Raw J-Link command is disabled", "RAW_COMMAND_DISABLED", recoverable=False)
        if len(command) > cfg.safety.max_raw_command_length:
            raise MCPError("Raw command exceeds configured length limit", "SAFETY_LIMIT")
        with service.session.operation():
            return {"output": service.jlink.raw(command)}
    return call("jlink_command", op)


def main() -> None:
    mcp.run(transport="stdio")
