"""Typed errors raised by the Manus HTTP client."""

from __future__ import annotations


class ManusError(Exception):
    """Base class for all Manus-related errors."""


class ManusApiError(ManusError):
    """Raised when the Manus API returns `{ok: false, error: {...}}` or a non-2xx status."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int | None = None,
        request_id: str | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        self.request_id = request_id
        parts = [f"{code}: {message}"]
        if http_status is not None:
            parts.append(f"http={http_status}")
        if request_id:
            parts.append(f"request_id={request_id}")
        super().__init__(" | ".join(parts))


class ManusNetworkError(ManusError):
    """Raised when the HTTP call itself fails (DNS, connection, timeout) after retries."""

    def __init__(self, message: str, *, original: BaseException | None = None) -> None:
        self.original = original
        super().__init__(message)


class ManusConfigError(ManusError):
    """Raised for misconfiguration that should stop the process at startup."""
