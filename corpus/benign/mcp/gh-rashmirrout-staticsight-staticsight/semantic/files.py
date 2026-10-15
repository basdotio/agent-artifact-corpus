"""Which files are indexed, their language, and why others are skipped (shared rules: shared/semantic/languages.json)."""

from __future__ import annotations

from dataclasses import dataclass

from ..shared import shared_json

MAX_LINE_CHARS = 5000        # a line longer than this marks a minified/generated file
MINIFIED_AVG_LINE = 300      # average line length above this marks a minified/generated file
BINARY_SNIFF_BYTES = 8192


def rules() -> dict:
    return shared_json("semantic/languages.json")


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _ext(name: str) -> str:
    dot = name.rfind(".")
    return name[dot:].lower() if dot > 0 else ""


def language_of(path: str) -> str:
    r = rules()
    name = _basename(path)
    if name in r["filenames"]:
        return r["filenames"][name]
    return r["extensions"].get(_ext(name), "text")


def is_structural(language: str) -> bool:
    return language in rules()["structural"]


def pre_skip_reason(path: str, size: int, max_kb: int) -> str:
    """Skip decision from the name and size alone (no file read)."""
    r = rules()
    name = _basename(path)
    low = name.lower()
    if name in r["skip_filenames"]:
        return "generated"
    if any(low.endswith(s) for s in r["skip_suffixes"]):
        return "generated"
    if _ext(name) in r["skip_extensions"]:
        return "binary"
    if size > max_kb * 1024:
        return "too-large"
    if size == 0:
        return "empty"
    return ""


def content_skip_reason(data: bytes, text: str) -> str:
    """Skip decision from the content: binary (NUL bytes without a UTF-16 BOM) or minified/generated."""
    head = data[:BINARY_SNIFF_BYTES]
    utf16 = head.startswith((b"\xff\xfe", b"\xfe\xff"))
    if not utf16 and b"\x00" in head:
        return "binary"
    lines = text.split("\n")
    if not any(ln.strip() for ln in lines):
        return "empty"
    longest = max(len(ln) for ln in lines)
    avg = len(text) / max(len(lines), 1)
    if longest > MAX_LINE_CHARS or avg > MINIFIED_AVG_LINE:
        return "minified"
    return ""


@dataclass(frozen=True)
class FileStat:
    path: str
    size: int
    mtime_ns: str
