from __future__ import annotations

from ..config import Config
from ..errors import MCPError


class SafetyPolicy:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def require_read_write_mode(self, operation: str) -> None:
        if self.cfg.safety.mode == "read_only":
            raise MCPError(
                f"{operation} is disabled in read-only mode",
                "READ_ONLY_MODE",
                recoverable=False,
            )

    def require_confirmation(self, provided: str, expected: str) -> None:
        if provided != expected:
            raise MCPError(
                f"Explicit confirmation required: provide exactly {expected}",
                "SAFETY_CONFIRMATION_REQUIRED",
            )

    def check_read_length(self, length: int) -> None:
        if length <= 0:
            raise MCPError("length must be positive", "INVALID_ARGUMENT")
        if length > self.cfg.safety.max_memory_read_bytes:
            raise MCPError("memory read exceeds configured safety limit", "SAFETY_LIMIT")

    def check_write_length(self, length: int) -> None:
        if length <= 0:
            raise MCPError("data must not be empty", "INVALID_ARGUMENT")
        if length > self.cfg.safety.max_memory_write_bytes:
            raise MCPError("memory write exceeds configured safety limit", "SAFETY_LIMIT")
