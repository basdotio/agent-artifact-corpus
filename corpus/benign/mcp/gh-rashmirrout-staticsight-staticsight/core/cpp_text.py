"""Lightweight C++ text utilities: comment/string stripping (length preserving) and doc-comment extraction."""

from __future__ import annotations

import re
from typing import Sequence

_RAW_PREFIX = re.compile(r'(?:u8|u|U|L)?R"([^()\\\s]{0,16})\(')


def _is_word(ch: str) -> bool:
    return bool(ch) and (ch == "_" or ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9"))


def strip_code(lines: Sequence[str]) -> list[str]:
    """Blank out comments and the contents of string/char literals, preserving every column position.

    The result keeps quotes so `"..."` still looks like a literal, but no keyword or identifier inside a
    comment or string can be mistaken for code.
    """
    out: list[str] = []
    in_block = False
    raw_end: str | None = None
    for line in lines:
        chars = list(line)
        n = len(chars)
        i = 0
        while i < n:
            if raw_end is not None:
                j = line.find(raw_end, i)
                if j < 0:
                    for k in range(i, n):
                        chars[k] = " "
                    i = n
                    break
                for k in range(i, j):
                    chars[k] = " "
                i = j + len(raw_end)
                raw_end = None
                continue
            if in_block:
                j = line.find("*/", i)
                if j < 0:
                    for k in range(i, n):
                        chars[k] = " "
                    i = n
                    break
                for k in range(i, j + 2):
                    chars[k] = " "
                i = j + 2
                in_block = False
                continue
            c = line[i]
            nxt = line[i + 1] if i + 1 < n else ""
            if c == "/" and nxt == "/":
                for k in range(i, n):
                    chars[k] = " "
                break
            if c == "/" and nxt == "*":
                chars[i] = chars[i + 1] = " "
                i += 2
                in_block = True
                continue
            if c in "uULR" and (i == 0 or not _is_word(line[i - 1])):
                m = _RAW_PREFIX.match(line, i)
                if m:
                    raw_end = ")" + m.group(1) + '"'
                    i = m.end()
                    continue
            if c == '"':
                j = i + 1
                while j < n and line[j] != '"':
                    j += 2 if line[j] == "\\" else 1
                for k in range(i + 1, min(j, n)):
                    chars[k] = " "
                i = j + 1
                continue
            if c == "'":
                t = i
                while t > 0 and _is_word(line[t - 1]):
                    t -= 1
                if t < i and "0" <= line[t] <= "9":
                    i += 1  # digit separator, e.g. 1'000'000
                    continue
                j = i + 1
                while j < n and line[j] != "'":
                    j += 2 if line[j] == "\\" else 1
                for k in range(i + 1, min(j, n)):
                    chars[k] = " "
                i = j + 1
                continue
            i += 1
        out.append("".join(chars))
    return out


_SKIP_ABOVE = re.compile(r"^\s*(template\s*<.*|\[\[.*\]\]\s*|__attribute__.*|[A-Z][A-Z0-9_]*(\(.*\))?\s*)$")
_TRAILING_DOC = re.compile(r"(///<|//!<|/\*\*<)(.*?)(\*/)?\s*$")


def _clean_comment_line(text: str) -> str:
    t = text.strip()
    for marker in ("/**", "/*!", "/*", "///", "//!", "//"):
        if t.startswith(marker):
            t = t[len(marker):]
            break
    if t.endswith("*/"):
        t = t[:-2]
    t = t.strip()
    if t.startswith("*") and not t.startswith("*/"):
        t = t[1:].strip()
    return t.rstrip()


def extract_leading_comment(lines: Sequence[str], def_idx: int, max_lines: int = 40) -> list[str]:
    """Return the cleaned doc comment directly above lines[def_idx] (0-based), or a trailing ///< comment."""
    if not (0 <= def_idx < len(lines)):
        return []
    m = _TRAILING_DOC.search(lines[def_idx])
    trailing = [m.group(2).strip()] if m and m.group(2).strip() else []
    i = def_idx - 1
    skipped = 0
    while i >= 0 and skipped < 3 and _SKIP_ABOVE.match(lines[i]) and not lines[i].strip().startswith(("//", "/*", "*")):
        if not lines[i].strip():
            break
        i -= 1
        skipped += 1
    if i < 0:
        return trailing
    collected: list[str] = []
    stripped = lines[i].strip()
    if stripped.endswith("*/"):
        j = i
        while j >= 0 and def_idx - j <= max_lines:
            collected.append(lines[j])
            if "/*" in lines[j]:
                break
            j -= 1
        else:
            return trailing
        if j < 0:
            return trailing
        collected.reverse()
    elif stripped.startswith("//"):
        j = i
        while j >= 0 and lines[j].strip().startswith("//") and def_idx - j <= max_lines:
            collected.append(lines[j])
            j -= 1
        collected.reverse()
    else:
        return trailing
    cleaned = [_clean_comment_line(c) for c in collected]
    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return cleaned or trailing


def balanced_parens(code: str, start: int = 0) -> tuple[int, int] | None:
    """Find the first '(' at/after start and its matching ')'. Returns (open_idx, close_idx) or None."""
    open_idx = code.find("(", start)
    if open_idx < 0:
        return None
    depth = 0
    for k in range(open_idx, len(code)):
        if code[k] == "(":
            depth += 1
        elif code[k] == ")":
            depth -= 1
            if depth == 0:
                return open_idx, k
    return open_idx, len(code)
