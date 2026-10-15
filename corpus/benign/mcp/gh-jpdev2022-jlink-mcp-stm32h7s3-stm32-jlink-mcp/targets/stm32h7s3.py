from __future__ import annotations

from ..models import MemoryRegion, TargetProfile


# STM32H7S3I8 is the MCU family/profile used by the user's LQFP176 board.
# SEGGER's supported-device database names the J-Link target STM32H7S3I8; the
# physical ordering code is STM32H7S3I8T6.
#
# The profile uses the architectural memory windows from RM0477 rather than
# pretending that the shared/remappable TCM/AXI portions are permanently assigned.
# RM0477 Rev. 8 defines 0x00000000-0x0002FFFF for ITCM, 0x20000000-0x2002FFFF
# for DTCM, and 0x24000000-0x24071FFF for AXI SRAM. Portions of these windows
# are shared/remappable; runtime option-byte/remap state determines the effective
# partition. The profile therefore treats them as addressable windows for safety
# classification, not as a linker-script prescription.
#
# External NOR is board-specific and is therefore configured separately. For the
# current board, XSPI1 maps at 0x90000000 and the 512-Mbit NOR occupies 64 MiB.
STM32H7S3I8_PROFILE = TargetProfile(
    name="STM32H7S3I8",
    core="Cortex-M7",
    regions=(
        MemoryRegion("itcm", 0x00000000, 0x0002FFFF, True, True),
        MemoryRegion("user_flash", 0x08000000, 0x0800FFFF, False, True),
        MemoryRegion("system_flash", 0x1FF00000, 0x1FF1FFFF, False, True),
        MemoryRegion("dtcm_ram", 0x20000000, 0x2002FFFF, True, True),
        MemoryRegion("axi_sram", 0x24000000, 0x24071FFF, True, True),
        MemoryRegion("sram_ahb", 0x30000000, 0x30007FFF, True, False),
        MemoryRegion("backup_sram", 0x38800000, 0x38800FFF, True, False),
        MemoryRegion("peripherals", 0x40000000, 0x5FFFFFFF, True, False),
        MemoryRegion("fmc_external_window", 0x60000000, 0x6FFFFFFF, False, False),
        MemoryRegion("xspi2_window", 0x70000000, 0x7FFFFFFF, False, False),
        MemoryRegion("xspi1_window", 0x90000000, 0x9FFFFFFF, False, False),
    ),
)

# Backwards-compatible family alias.
STM32H7S3_PROFILE = STM32H7S3I8_PROFILE
