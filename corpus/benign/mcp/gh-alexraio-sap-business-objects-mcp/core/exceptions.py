"""
Custom exceptions for SAP BusinessObjects BI Platform SDK and MCP tools.
"""

from typing import Any, Optional


class BOEError(Exception):
    """Base exception for all SAP BusinessObjects errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

    def __str__(self) -> str:
        if self.status_code:
            return f"[HTTP {self.status_code}] {self.message}"
        return self.message


class BOEAuthError(BOEError):
    """Raised when authentication, logon token acquisition, or session validation fails."""

    pass


class BOENotFoundError(BOEError):
    """Raised when a requested resource (document, universe, folder, user) is not found (HTTP 404)."""

    pass


class BOEProcessingError(BOEError):
    """Raised when the Web Intelligence Processing Server or Raylight encounters an engine failure (e.g. WSR 00999)."""

    pass


class BOEQueryError(BOEError):
    """Raised when a CMS SQL query fails to execute or syntax is invalid."""

    pass
