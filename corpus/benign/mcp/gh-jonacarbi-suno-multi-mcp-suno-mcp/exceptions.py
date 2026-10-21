"""Custom exceptions for Suno MCP Server."""


class SunoError(Exception):
    """Base exception for Suno MCP operations."""

    def __init__(self, message: str, code: str = "SUNO_ERROR") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class BrowserError(SunoError):
    """Browser-related errors."""

    def __init__(self, message: str, code: str = "BROWSER_ERROR") -> None:
        super().__init__(message, code)


class AuthError(SunoError):
    """Authentication-related errors."""

    def __init__(self, message: str, code: str = "AUTH_ERROR") -> None:
        super().__init__(message, code)


class NavigationError(SunoError):
    """Navigation/page-related errors."""

    def __init__(self, message: str, code: str = "NAVIGATION_ERROR") -> None:
        super().__init__(message, code)
