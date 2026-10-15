from __future__ import annotations

from typing import Any

from ..errors import MCPError
from ..probe.jlink import JLinkBackend


FAULT_REGISTERS = {
    "ICSR": 0xE000ED04,
    "SHCSR": 0xE000ED24,
    "CFSR": 0xE000ED28,
    "HFSR": 0xE000ED2C,
    "DFSR": 0xE000ED30,
    "MMFAR": 0xE000ED34,
    "BFAR": 0xE000ED38,
    "AFSR": 0xE000ED3C,
}


def read_fault_info(jlink: JLinkBackend) -> dict[str, Any]:
    values: dict[str, int | None] = {}
    for name, address in FAULT_REGISTERS.items():
        try:
            raw = bytes.fromhex(jlink.read_memory(address, 4)["data_hex"])
            values[name] = int.from_bytes(raw, "little") if len(raw) == 4 else None
        except MCPError:
            values[name] = None

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
    }
