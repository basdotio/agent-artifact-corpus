"""STM32H7S3 option-byte helpers.

This module intentionally treats option bytes as a dangerous, device-specific
operation. The STM32H7S3 exposes current and programming option-byte registers
through the FLASH peripheral; writing requires the STM32 flash option-byte
unlock/program/launch sequence. Prefer the official STM32 tooling or a
device-specific implementation rather than guessing register layouts.

For v0.2.3 the MCP exposes a safe read path and a guarded backend interface for
write/mass-erase operations. The backend is intentionally not implemented by
blind raw register writes.
"""

from dataclasses import dataclass
from enum import Enum


class OptionByteOperation(str, Enum):
    READ = "read"
    WRITE = "write"
    MASS_ERASE = "mass_erase"


@dataclass(frozen=True)
class OptionByteWriteRequest:
    register: str
    value: int
    confirmation: str


READ_ONLY_REGISTERS = {
    "FLASH_OPTSR_CUR",
    "FLASH_OBW1SR",
    "FLASH_OBW2SR",
    "FLASH_NVSR",
    "FLASH_ROTSR",
    "FLASH_OTPLSR",
    "FLASH_WRPSR",
    "FLASH_HDPSR",
    "FLASH_EPOCHSR",
}

WRITE_REGISTERS = {
    "FLASH_OPTSR_PRG",
    "FLASH_OBW1SRP",
    "FLASH_OBW2SRP",
    "FLASH_NVSRP",
    "FLASH_ROTSRP",
    "FLASH_OTPLSRP",
    "FLASH_WRPSRP",
    "FLASH_HDPSRP",
    "FLASH_EPOCHSRP",
}


def validate_write(request: OptionByteWriteRequest) -> None:
    if request.register not in WRITE_REGISTERS:
        raise ValueError(
            f"{request.register} is not an approved STM32H7S3 programming register"
        )
    if not 0 <= request.value <= 0xFFFFFFFF:
        raise ValueError("option-byte register value must be a 32-bit unsigned value")
    if request.confirmation != "PROGRAM_OPTION_BYTES":
        raise ValueError("confirmation must be PROGRAM_OPTION_BYTES")


def validate_mass_erase(confirmation: str) -> None:
    if confirmation != "MASS_ERASE_INTERNAL_FLASH":
        raise ValueError("confirmation must be MASS_ERASE_INTERNAL_FLASH")
