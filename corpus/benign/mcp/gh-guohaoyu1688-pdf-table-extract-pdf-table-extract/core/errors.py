"""Stable machine-readable errors."""

from typing import Any


class PDFError(Exception):
    def __init__(self, code: str, message: str, exit_code: int = 1):
        super().__init__(message)
        self.code, self.exit_code = code, exit_code


def success(data: Any) -> dict:
    return {"ok": True, "data": data, "warnings": []}


def failure(error: PDFError) -> dict:
    return {"ok": False, "error": {"code": error.code, "message": str(error)}}
