from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import MCPError


class ElfSymbols:
    def __init__(self):
        self.path: str | None = None
        self.symbols: dict[str, int] = {}

    def load(self, path: str) -> dict[str, Any]:
        from elftools.elf.elffile import ELFFile

        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise MCPError(f"ELF does not exist: {p}", "ELF_NOT_FOUND")
        symbols: dict[str, int] = {}
        with p.open("rb") as f:
            elf = ELFFile(f)
            for section_name in (".symtab", ".dynsym"):
                section = elf.get_section_by_name(section_name)
                if section is None:
                    continue
                for sym in section.iter_symbols():
                    name = sym.name
                    value = int(sym["st_value"])
                    if name and value:
                        symbols.setdefault(name, value)
        self.path = str(p)
        self.symbols = symbols
        return {"loaded": True, "path": self.path, "symbols": len(self.symbols)}

    def symbol(self, name: str) -> dict[str, Any]:
        value = self.symbols.get(name)
        if value is None:
            return {"found": False, "symbol": name}
        return {"found": True, "symbol": name, "address": f"0x{value:08X}"}

    def address(self, address: int) -> dict[str, Any]:
        candidates = [(value, name) for name, value in self.symbols.items() if value <= address]
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
