from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import MCPError


@dataclass(frozen=True)
class SvdField:
    name: str
    bit_offset: int
    bit_width: int
    description: str = ""


@dataclass(frozen=True)
class SvdRegister:
    name: str
    address_offset: int
    size_bits: int
    access: str
    description: str = ""
    fields: tuple[SvdField, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SvdPeripheral:
    name: str
    base_address: int
    description: str
    registers: tuple[SvdRegister, ...]

    def register(self, name: str) -> SvdRegister | None:
        wanted = name.upper()
        for reg in self.registers:
            if reg.name.upper() == wanted:
                return reg
        return None


class SvdDatabase:
    def __init__(self):
        self.path: str | None = None
        self.device_name: str | None = None
        self.peripherals: dict[str, SvdPeripheral] = {}

    def load(self, path: str) -> dict[str, Any]:
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise MCPError(f"SVD does not exist: {p}", "SVD_NOT_FOUND")
        root = ET.parse(p).getroot()
        self.path = str(p)
        self.device_name = text(root.find("name"))
        self.peripherals.clear()
        periph_root = root.find("peripherals")
        if periph_root is None:
            raise MCPError("SVD contains no peripherals", "SVD_INVALID")
        for node in periph_root.findall("peripheral"):
            name = text(node.find("name"))
            base = parse_int(text(node.find("baseAddress")))
            regs_node = node.find("registers")
            regs: list[SvdRegister] = []
            if regs_node is not None:
                for r in regs_node.findall("register"):
                    fields: list[SvdField] = []
                    fields_node = r.find("fields")
                    if fields_node is not None:
                        for f in fields_node.findall("field"):
                            offset, width = field_bits(f)
                            fields.append(SvdField(
                                text(f.find("name")), offset, width, text(f.find("description"))
                            ))
                    regs.append(SvdRegister(
                        name=text(r.find("name")),
                        address_offset=parse_int(text(r.find("addressOffset"))),
                        size_bits=parse_int(text(r.find("size"))) or 32,
                        access=text(r.find("access")) or "read-write",
                        description=text(r.find("description")),
                        fields=tuple(fields),
                    ))
            self.peripherals[name] = SvdPeripheral(
                name=name,
                base_address=base,
                description=text(node.find("description")),
                registers=tuple(regs),
            )
        return {"loaded": True, "path": self.path, "device": self.device_name, "peripherals": len(self.peripherals)}

    def info(self) -> dict[str, Any]:
        return {
            "loaded": bool(self.path),
            "path": self.path,
            "device": self.device_name,
            "peripherals": len(self.peripherals),
        }

    def _peripheral(self, name: str) -> SvdPeripheral | None:
        wanted = name.upper()
        for peripheral in self.peripherals.values():
            if peripheral.name.upper() == wanted:
                return peripheral
        return None

    def peripheral_info(self, name: str) -> dict[str, Any]:
        p = self._peripheral(name)
        if p is None:
            raise MCPError(f"Peripheral not found: {name}", "SVD_PERIPHERAL_NOT_FOUND")
        return {
            "name": p.name,
            "base_address": f"0x{p.base_address:08X}",
            "description": p.description,
            "registers": [r.name for r in p.registers],
        }

    def register_info(self, peripheral: str, register: str) -> dict[str, Any]:
        p = self._peripheral(peripheral)
        if p is None:
            raise MCPError(f"Peripheral not found: {peripheral}", "SVD_PERIPHERAL_NOT_FOUND")
        r = p.register(register)
        if r is None:
            raise MCPError(f"Register not found: {peripheral}.{register}", "SVD_REGISTER_NOT_FOUND")
        return {
            "peripheral": p.name,
            "register": r.name,
            "address": f"0x{p.base_address + r.address_offset:08X}",
            "size_bits": r.size_bits,
            "access": r.access,
            "description": r.description,
            "fields": [
                {"name": f.name, "bit_offset": f.bit_offset, "bit_width": f.bit_width, "description": f.description}
                for f in r.fields
            ],
        }


def text(node: ET.Element | None) -> str:
    return (node.text or "").strip() if node is not None else ""


def parse_int(value: str) -> int:
    if not value:
        return 0
    return int(value, 0)


def field_bits(node: ET.Element) -> tuple[int, int]:
    bit_offset = node.findtext("bitOffset")
    bit_width = node.findtext("bitWidth")
    if bit_offset is not None and bit_width is not None:
        return int(bit_offset, 0), int(bit_width, 0)
    lsb = node.findtext("lsb")
    msb = node.findtext("msb")
    if lsb is not None and msb is not None:
        l, m = int(lsb, 0), int(msb, 0)
        return l, m - l + 1
    return 0, 0
