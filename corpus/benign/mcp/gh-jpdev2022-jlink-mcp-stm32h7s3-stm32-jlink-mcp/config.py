from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TargetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Exact physical part on the user's board. SEGGER identifies the supported
    # J-Link device as STM32H7S3I8 (without package/temperature suffix).
    device: str = "STM32H7S3I8T6"
    jlink_device: str = "STM32H7S3I8"
    package: str = "LQFP176"
    interface: str = "SWD"
    speed_khz: int = Field(default=4000, ge=1, le=50000)
    jlink_serial: int | None = Field(default=None, gt=0)


class ExecutablesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jlink: str = "JLinkExe"
    gdb_server: str = "JLinkGDBServer"
    gdb: str = "arm-none-eabi-gdb"


class ExternalFlashConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    controller: Literal["XSPI1", "XSPI2"] = "XSPI1"
    mapped_address: int = Field(default=0x90000000, ge=0)
    # 512 Mbit = 64 MiB for the selected Macronix device.
    size: int = Field(default=64 * 1024 * 1024, ge=0)
    part_number: str = "MX25UW51245GXDI00"
    density_bits: int = Field(default=512 * 1024 * 1024, ge=1)
    voltage_min_v: float = Field(default=1.65, gt=0)
    voltage_max_v: float = Field(default=2.0, gt=0)
    max_clock_mhz: int = Field(default=200, ge=1)
    protocol: str = "Octal I/O / DTR-capable"
    chip_select: str = "NCS1"
    jedec_id: str | None = "C2 81 3A"
    # HAL_XSPI_SIZE_512MB corresponds to 512 Mbit = 64 MiB. The HAL naming is
    # historical and uses MB here to mean megabits, not megabytes.
    hal_memory_size: str = "HAL_XSPI_SIZE_512MB"

    @model_validator(mode="after")
    def validate_geometry(self) -> "ExternalFlashConfig":
        expected_base = {"XSPI1": 0x90000000, "XSPI2": 0x70000000}[self.controller]
        if self.mapped_address != expected_base:
            raise ValueError(
                f"{self.controller} mapped_address must be 0x{expected_base:08X} for STM32H7S3"
            )
        if self.size and self.density_bits != self.size * 8:
            raise ValueError("external_flash.size must equal density_bits / 8")
        if self.size and self.size > 0x10000000:
            raise ValueError("external_flash.size exceeds the 256 MiB XSPI address window")
        return self


class SvdConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str | None = None


class ElfConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str | None = None


class RttConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    host: str = "127.0.0.1"
    telnet_port: int = Field(default=19021, ge=1024, le=65535)
    max_read_bytes: int = Field(default=4096, ge=1, le=1024 * 1024)
    max_write_bytes: int = Field(default=4096, ge=1, le=1024 * 1024)
    connect_timeout_s: float = Field(default=3.0, gt=0, le=30)
    read_timeout_s: float = Field(default=0.25, gt=0, le=30)
    control_block: int | None = Field(default=None, ge=0)
    search_ranges: list[str] = Field(default_factory=list)


class DebugConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gdb_port: int = Field(default=2331, ge=1024, le=65535)
    gdb_startup_timeout_s: float = Field(default=8.0, gt=0)
    gdb_command_timeout_s: float = Field(default=5.0, gt=0)
    gdb_poll_interval_s: float = Field(default=0.05, gt=0)


class SafetyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["normal", "read_only"] = "normal"
    require_write_confirmation: bool = True
    require_flash_confirmation: bool = True
    max_memory_read_bytes: int = Field(default=65536, ge=1, le=16 * 1024 * 1024)
    max_memory_write_bytes: int = Field(default=4096, ge=1, le=1024 * 1024)
    max_raw_command_length: int = Field(default=256, ge=1, le=4096)
    allow_raw_jlink_command: bool = False


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: TargetConfig = Field(default_factory=TargetConfig)
    executables: ExecutablesConfig = Field(default_factory=ExecutablesConfig)
    external_flash: ExternalFlashConfig = Field(default_factory=ExternalFlashConfig)
    svd: SvdConfig = Field(default_factory=SvdConfig)
    elf: ElfConfig = Field(default_factory=ElfConfig)
    debug: DebugConfig = Field(default_factory=DebugConfig)
    rtt: RttConfig = Field(default_factory=RttConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)


def load_config(path: str | None = None) -> Config:
    config_path = Path(path or os.environ.get("STM32_JLINK_MCP_CONFIG", "config.yaml"))
    if not config_path.exists():
        return Config()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return Config.model_validate(raw)
