"""Language-agnostic chunking into embeddable units.

- structural languages (ctags): one chunk per innermost function/class/..., container "gap" chunks for members that
  are not inside a nested unit, and file-level gap chunks (includes, globals, defines);
- markdown: one chunk per heading section;
- anything else: line windows.
Every chunk longer than MAX_CHARS is split into overlapping line windows (parts). The chunker is model-independent,
so Python and TypeScript produce identical chunks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..engines.ctags import Tag
from .files import is_structural, rules

MAX_CHARS = 1200          # ~300-400 code tokens: fast to embed, precise to retrieve
WINDOW_OVERLAP = 2        # lines shared by consecutive windows
LINE_CLIP = 300           # characters kept per line in the embedded text
MAX_COMMENT_LINES = 15    # leading comment lines attached to a unit
_SIGNIFICANT = re.compile(r"[A-Za-z0-9]")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
CONTAINER_KINDS = frozenset({
    "class", "struct", "union", "enum", "interface", "trait", "impl", "implementation", "namespace", "module",
    "type", "record", "protocol", "object", "package", "anonymousClass",
})


@dataclass
class Chunk:
    path: str
    start_line: int
    end_line: int
    language: str
    kind: str
    symbol: str
    signature: str
    part: int = 0
    text: str = field(default="", repr=False)   # the embedded text (header + body)


def _significant(line: str) -> bool:
    return bool(_SIGNIFICANT.search(line))


def _header(path: str, kind: str, symbol: str, signature: str, part: int) -> str:
    h = f"{path} | {kind}"
    if symbol:
        h += f" {symbol}"
    if signature:
        h += f" | {signature}"
    if part:
        h += f" (part {part + 1})"
    return h


def _windows(start: int, end: int, lines: list[str]) -> list[tuple[int, int]]:
    """Split [start, end] (1-based, inclusive) into windows under MAX_CHARS with WINDOW_OVERLAP lines of overlap."""
    out: list[tuple[int, int]] = []
    s = start
    while s <= end:
        size = 0
        e = s
        while e <= end:
            add = min(len(lines[e - 1]), LINE_CLIP) + 1
            if size + add > MAX_CHARS and e > s:
                break
            size += add
            e += 1
        e -= 1
        out.append((s, e))
        if e >= end:
            break
        s = max(e - WINDOW_OVERLAP + 1, s + 1)
    return out


def _emit(chunks: list[Chunk], path: str, lines: list[str], start: int, end: int, language: str, kind: str,
          symbol: str, signature: str) -> None:
    for part, (a, b) in enumerate(_windows(start, end, lines)):
        body = "\n".join(ln[:LINE_CLIP] for ln in lines[a - 1 : b])
        chunks.append(Chunk(path, a, b, language, kind, symbol, signature, part,
                            _header(path, kind, symbol, signature, part) + "\n" + body))


def _ranges(covered: list[bool], lo: int, hi: int) -> list[tuple[int, int]]:
    """Maximal uncovered runs of lines within [lo, hi] (1-based)."""
    runs: list[tuple[int, int]] = []
    s = None
    for n in range(lo, hi + 1):
        if not covered[n]:
            if s is None:
                s = n
        elif s is not None:
            runs.append((s, n - 1))
            s = None
    if s is not None:
        runs.append((s, hi))
    return runs


def _trim(lines: list[str], a: int, b: int) -> tuple[int, int] | None:
    while a <= b and not lines[a - 1].strip():
        a += 1
    while b >= a and not lines[b - 1].strip():
        b -= 1
    if a > b or sum(1 for n in range(a, b + 1) if _significant(lines[n - 1])) < 2:
        return None
    return a, b


def _is_comment(line: str, prefixes: list[str]) -> bool:
    s = line.strip()
    return bool(s) and any(s.startswith(p) for p in prefixes)


def chunk_structural(path: str, lines: list[str], language: str, tags: list[Tag]) -> list[Chunk]:
    unit_kinds = set(rules()["unit_kinds"])
    n = len(lines)
    seen: set[tuple[int, int]] = set()
    units: list[Tag] = []
    for t in sorted(tags, key=lambda t: (t.line, -t.end, t.name)):
        end = min(t.end, n)
        # multi-line units only: one-line members/functions stay in the surrounding gap chunk
        if t.kind not in unit_kinds or t.line < 1 or t.line > n or end <= t.line:
            continue
        if (t.line, end) in seen:
            continue
        seen.add((t.line, end))
        units.append(Tag(t.name, t.kind, t.line, end, t.path, t.scope, t.scope_kind, t.signature, t.typeref))

    def contains(a: Tag, b: Tag) -> bool:
        return a is not b and a.line <= b.line and b.end <= a.end and (a.line, a.end) != (b.line, b.end)

    children = {id(u): [v for v in units if contains(u, v)] for u in units}
    leaves = [u for u in units if not children[id(u)]]
    containers = [u for u in units if children[id(u)]]  # incl. functions with nested functions/lambdas
    prefixes = rules()["comment_prefixes"].get(language, [])
    covered = [False] * (n + 2)
    for u in units:
        for k in range(u.line, u.end + 1):
            covered[k] = True

    attached = [False] * (n + 2)   # leading comment lines already given to a unit
    comment_start: dict[int, int] = {}

    def attach_comments(u: Tag) -> int:
        start = u.line
        k = u.line - 1
        steps = 0
        while k >= 1 and steps < MAX_COMMENT_LINES and not covered[k] and _is_comment(lines[k - 1], prefixes):
            start = k
            k -= 1
            steps += 1
        for c in range(start, u.line):
            covered[c] = True
            attached[c] = True
        return start

    for u in sorted(leaves + containers, key=lambda u: (-u.line, u.end)):  # bottom-up: inner comments first
        comment_start[id(u)] = attach_comments(u)
    chunks: list[Chunk] = []
    for u in leaves:
        sig = u.signature if u.kind not in CONTAINER_KINDS else ""
        _emit(chunks, path, lines, comment_start[id(u)], u.end, language, u.kind, u.qualified, sig)
    for u in containers:
        inner = list(attached)
        for v in children[id(u)]:
            for k in range(v.line, v.end + 1):
                inner[k] = True
        sig = u.signature if u.kind not in CONTAINER_KINDS else ""
        for a, b in _ranges(inner, u.line, u.end):
            if a == u.line:
                a = comment_start[id(u)]
            tr = _trim(lines, a, b)
            if tr:
                _emit(chunks, path, lines, tr[0], tr[1], language, u.kind, u.qualified, sig)
    for a, b in _ranges(covered, 1, n):
        tr = _trim(lines, a, b)
        if tr:
            _emit(chunks, path, lines, tr[0], tr[1], language, "file", "", "")
    chunks.sort(key=lambda c: (c.start_line, c.end_line, c.part, c.kind, c.symbol))
    return chunks


def chunk_markdown(path: str, lines: list[str], language: str) -> list[Chunk]:
    heads: list[tuple[int, str]] = []
    fence = False
    for i, ln in enumerate(lines, 1):
        if ln.lstrip().startswith(("```", "~~~")):
            fence = not fence
            continue
        m = None if fence else _HEADING.match(ln)
        if m:
            heads.append((i, m.group(2)))
    bounds: list[tuple[int, int, str]] = []
    if not heads or heads[0][0] > 1:
        bounds.append((1, (heads[0][0] - 1) if heads else len(lines), ""))
    for j, (ln, title) in enumerate(heads):
        end = heads[j + 1][0] - 1 if j + 1 < len(heads) else len(lines)
        bounds.append((ln, end, title))
    chunks: list[Chunk] = []
    for a, b, title in bounds:
        if title:
            while b > a and not lines[b - 1].strip():
                b -= 1
            tr: tuple[int, int] | None = (a, b)
        else:
            tr = _trim(lines, a, b)
        if tr and any(_significant(lines[k - 1]) for k in range(tr[0], tr[1] + 1)):
            _emit(chunks, path, lines, tr[0], tr[1], language, "section", title, "")
    return chunks


def chunk_plain(path: str, lines: list[str], language: str) -> list[Chunk]:
    tr = _trim(lines, 1, len(lines))
    if not tr:
        a = next((i for i, ln in enumerate(lines, 1) if _significant(ln)), 0)
        if not a:
            return []
        tr = (a, a)
    chunks: list[Chunk] = []
    _emit(chunks, path, lines, tr[0], tr[1], language, "window", "", "")
    return chunks


def chunk_file(path: str, lines: list[str], language: str, tags: list[Tag] | None) -> list[Chunk]:
    if language == "markdown":
        return chunk_markdown(path, lines, language)
    if is_structural(language) and tags:
        return chunk_structural(path, lines, language, tags)
    return chunk_plain(path, lines, language)
