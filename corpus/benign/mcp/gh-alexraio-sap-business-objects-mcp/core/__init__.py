"""
Core networking, authentication, and exception handling for SAP BusinessObjects.
"""

from .exceptions import (
    BOEAuthError,
    BOEError,
    BOENotFoundError,
    BOEProcessingError,
    BOEQueryError,
)

__all__ = [
    "BOEError",
    "BOEAuthError",
    "BOENotFoundError",
    "BOEProcessingError",
    "BOEQueryError",
]
