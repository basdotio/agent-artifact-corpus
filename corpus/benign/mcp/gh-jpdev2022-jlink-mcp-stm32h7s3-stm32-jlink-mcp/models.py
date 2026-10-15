from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TargetState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    HALTED = "HALTED"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class MemoryRegion:
    name: str
    start: int
    end: int
    writable: bool = True
    executable: bool = False

    @property
    def size(self) -> int:
        return self.end - self.start + 1

    def contains(self, address: int, length: int = 1) -> bool:
        if length <= 0:
            return False
        last = address + length - 1
        return self.start <= address <= self.end and last <= self.end


@dataclass(frozen=True)
class TargetProfile:
    name: str
    core: str
    regions: tuple[MemoryRegion, ...]

    def region_for(self, address: int, length: int = 1) -> MemoryRegion | None:
        for region in self.regions:
            if region.contains(address, length):
                return region
        return None
