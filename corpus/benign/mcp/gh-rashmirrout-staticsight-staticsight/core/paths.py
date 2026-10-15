"""Workspace path confinement: every file argument must resolve inside WORKSPACE_ROOT."""

from __future__ import annotations

import os
from pathlib import Path

from ..platform import current as current_platform
from .errors import InvalidArgument, StaticSightError


class FileMissing(StaticSightError):
    title = "File not found"


def resolve_in_workspace(root: Path, file_path: str, must_exist: bool = True) -> tuple[Path, str]:
    """Return (absolute_path, workspace_relative_posix_path). Rejects paths escaping the workspace."""
    if not file_path or not str(file_path).strip():
        raise InvalidArgument("`file_path` is empty.", "Pass a path relative to the workspace root, e.g. `src/router.cpp`.")
    raw = str(file_path).strip()
    candidate = Path(raw) if os.path.isabs(raw) else root / raw
    real = Path(os.path.realpath(candidate))
    root_real = Path(os.path.realpath(root))
    try:
        rel = real.relative_to(root_real)
    except ValueError:
        raise InvalidArgument(
            f"`{raw}` is outside the workspace (WORKSPACE_ROOT).",
            "Only files inside WORKSPACE_ROOT can be inspected.",
        ) from None
    if must_exist and not real.is_file():
        raise FileMissing(
            f"`{rel.as_posix()}` does not exist (it may have been deleted or renamed).",
            "Check the path with get_diff_scopes, or pass a path relative to the workspace root.",
        )
    return real, rel.as_posix()


def decode_source(data: bytes) -> str:
    """Decode source bytes: honours UTF-8/UTF-16 BOMs (common in MSVC repos), else UTF-8 with replacement.

    The BOM is removed so that line-1 patterns such as `#include` still match.
    """
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", errors="replace")
    if data.startswith(b"\xff\xfe"):
        return data[2:].decode("utf-16-le", errors="replace")
    if data.startswith(b"\xfe\xff"):
        return data[2:].decode("utf-16-be", errors="replace")
    return data.decode("utf-8", errors="replace")


def read_lines(path: Path) -> list[str]:
    """Read a text file as lines without line terminators (CRLF-safe, undecodable bytes replaced)."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise FileMissing(f"`{path.name}` no longer exists.") from None
    except IsADirectoryError:
        raise InvalidArgument(f"`{path.name}` is a directory, not a file.") from None
    return split_lines(decode_source(data))


def split_lines(text: str) -> list[str]:
    """Lines without terminators (CRLF-safe); a trailing newline does not produce an empty last line."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [ln[:-1] if ln.endswith("\r") else ln for ln in lines]


def matches_glob(rel_path: str, pattern: str) -> bool:
    """fnmatch semantics ('*' also matches '/'); case-insensitive on case-insensitive platforms."""
    if not pattern:
        return True
    fm = current_platform().fnmatch
    pattern = pattern.replace("\\", "/")
    base = rel_path.rsplit("/", 1)[-1]
    return fm(rel_path, pattern) or fm(rel_path, pattern.rstrip("/") + "/*") or fm(base, pattern)
