#!/usr/bin/env python3
"""Find `@claude` / `@claude?` review markers inside source-code comments.

Deliberately conservative: a marker only counts when it opens a comment (or a line
inside a block comment) in a file whose comment syntax is known. Strings, template
literals and unknown file types (Markdown, plain text) are never scanned, so prose
that merely mentions the marker is not picked up.

Usage: find_markers.py [--json] [PATH ...]
  no PATH      every file git would track under the cwd (respects .gitignore);
               files carrying the SKIP_PRAGMA are left out
  PATH (file)  scanned even if untracked or gitignored
  PATH (dir)   like the default, limited to that directory
"""
import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SKIP_PRAGMA = "inline-comments: skip-in-repo-scan"
MAX_BYTES = 1_000_000
MARKER_RE = re.compile(r"^@claude(\?)?(?=\s|$)(.*)$", re.S)
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target"}


@dataclass(frozen=True)
class Lang:
    line: tuple = ()
    block: tuple = ()
    strings: tuple = ('"', "'")
    raw_strings: tuple = ()  # delimiters with no backslash escapes
    multiline_strings: tuple = ()  # delimiters that may span lines
    lifetimes: bool = False  # ' may be a Rust lifetime rather than a char literal


C_LIKE = Lang(line=("//",), block=(("/*", "*/"),))
RUST = Lang(line=("//",), block=(("/*", "*/"),), lifetimes=True)
JS = Lang(line=("//",), block=(("/*", "*/"),), strings=('"', "'", "`"), multiline_strings=("`",))
GO = Lang(line=("//",), block=(("/*", "*/"),), strings=('"', "'", "`"),
          raw_strings=("`",), multiline_strings=("`",))
PY = Lang(line=("#",), strings=('"""', "'''", '"', "'"), multiline_strings=('"""', "'''"))
HASH = Lang(line=("#",))
HCL = Lang(line=("#", "//"), block=(("/*", "*/"),), strings=('"',))
PHP = Lang(line=("//", "#"), block=(("/*", "*/"),))
SQL = Lang(line=("--",), block=(("/*", "*/"),), strings=("'", '"'))
DASH = Lang(line=("--",))
CSS = Lang(block=(("/*", "*/"),))
MARKUP = Lang(block=(("<!--", "-->"),), strings=())

LANGS = {
    **dict.fromkeys(["c", "h", "cc", "cpp", "cxx", "hpp", "cs", "java", "kt", "kts", "scala",
                     "swift", "dart", "groovy", "gradle", "proto"], C_LIKE),
    **dict.fromkeys(["js", "jsx", "mjs", "cjs", "ts", "tsx", "mts", "cts"], JS),
    "go": GO,
    "rs": RUST,
    **dict.fromkeys(["py", "pyi"], PY),
    **dict.fromkeys(["sh", "bash", "zsh", "rb", "pl", "r", "ps1", "yaml", "yml", "toml",
                     "nix", "cmake", "mk"], HASH),
    **dict.fromkeys(["tf", "tfvars", "hcl"], HCL),
    "php": PHP,
    "sql": SQL,
    **dict.fromkeys(["lua", "hs"], DASH),
    **dict.fromkeys(["css", "scss", "less"], CSS),
    **dict.fromkeys(["html", "htm", "xml", "vue", "svelte"], MARKUP),
}
BY_NAME = {"Makefile": HASH, "Dockerfile": HASH, "Containerfile": HASH, "Jenkinsfile": C_LIKE}


def lang_for(path):
    path = Path(path)
    return BY_NAME.get(path.name) or LANGS.get(path.suffix.lstrip(".").lower())


@dataclass
class Comment:
    start: int
    end: int
    opener: str
    closer: str = ""


@dataclass
class Marker:
    path: str
    line: int
    col: int
    kind: str  # edit | question
    instruction: str
    needs_clarification: bool
    removal: dict = field(default_factory=dict)  # empty for questions

    def as_dict(self):
        return self.__dict__.copy()


def _string_end(text, i, delim, lang):
    """Index just past the string literal whose opening delimiter ends at i."""
    escapes = delim not in lang.raw_strings
    multiline = delim in lang.multiline_strings
    n = len(text)
    while i < n:
        if escapes and text[i] == "\\":
            i += 2
            continue
        if text.startswith(delim, i):
            return i + len(delim)
        if text[i] == "\n" and not multiline:
            return i  # unterminated on this line: stop rather than swallow the file
        i += 1
    return n


def find_comments(text, lang):
    out, i, n = [], 0, len(text)
    strings = sorted(lang.strings, key=len, reverse=True)
    while i < n:
        delim = next((d for d in strings if text.startswith(d, i)), None)
        if delim:
            # A ' that does not close within a few chars is a lifetime, not a char literal.
            if delim == "'" and lang.lifetimes:
                close = text.find("'", i + 1, i + 5)
                if close == -1:
                    i += 1
                    continue
            i = _string_end(text, i + len(delim), delim, lang)
            continue
        line_op = next((op for op in lang.line if text.startswith(op, i)), None)
        # `#` only opens a comment at a word boundary (shell `$#`, `${#x}`, URLs).
        if line_op and (line_op != "#" or i == 0 or text[i - 1] in " \t\n"):
            end = text.find("\n", i)
            end = n if end == -1 else end
            out.append(Comment(i, end, line_op))
            i = end
            continue
        block = next((b for b in lang.block if text.startswith(b[0], i)), None)
        if block:
            close = text.find(block[1], i + len(block[0]))
            end = n if close == -1 else close + len(block[1])
            out.append(Comment(i, end, block[0], block[1]))
            i = end
            continue
        i += 1
    return out


def _line_bounds(text, pos):
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return start, len(text) if end == -1 else end


def _lineno(text, pos):
    return text.count("\n", 0, pos) + 1


def _strip_doc(s):
    """Drop decoration that precedes marker text: `///`, `//!`, ` * ` in block comments."""
    return s.lstrip().lstrip("/!*").lstrip()


def _marker(path, text, pos, body, removal):
    m = MARKER_RE.match(body)
    if not m:
        return None
    question = bool(m.group(1))
    instruction = " ".join(m.group(2).split())
    return Marker(
        path=str(path), line=_lineno(text, pos), col=pos - _line_bounds(text, pos)[0] + 1,
        kind="question" if question else "edit", instruction=instruction,
        needs_clarification=not instruction, removal={} if question else removal,
    )


def find_markers_in_text(text, lang, path="<text>"):
    markers = []
    for c in find_comments(text, lang):
        line_start, line_end = _line_bounds(text, c.start)
        before = text[line_start:c.start]
        standalone_start = not before.strip()

        if not c.closer:
            body = _strip_doc(text[c.start + len(c.opener):c.end])
            if standalone_start:
                removal = {"type": "lines", "start": _lineno(text, c.start), "end": _lineno(text, c.start)}
            else:
                cut = line_start + len(before.rstrip())
                removal = {"type": "span", "line": _lineno(text, c.start), "text": text[cut:c.end]}
            m = _marker(path, text, c.start, body, removal)
            if m:
                markers.append(m)
            continue

        inner_start = c.start + len(c.opener)
        inner_end = c.end - len(c.closer) if text.endswith(c.closer, 0, c.end) else c.end
        inner = text[inner_start:inner_end]
        last_start, last_end = _line_bounds(text, c.end - 1)
        standalone_end = not text[c.end:last_end].strip()

        if _strip_doc(inner).startswith("@claude"):
            lines = _strip_doc(inner).splitlines()
            rest = lines[1:-1] + [l for l in lines[-1:] if l.strip()] if len(lines) > 1 else []
            # Continuation lines only belong to the instruction when the comment is nothing
            # but the marker. A `*`-prefixed, blank or `@tag` line means the block also holds
            # docs (JSDoc, licence header): then only the opener line is the marker.
            if any(not l.strip() or l.lstrip().startswith(("*", "@")) for l in rest):
                mpos = c.start + text[c.start:].index("@claude")
                _, ln_end = _line_bounds(text, mpos)
                cut = len(text[:mpos].rstrip(" \t"))
                removal = {"type": "span", "line": _lineno(text, mpos), "text": text[cut:ln_end].rstrip()}
                m = _marker(path, text, mpos, lines[0].strip(), removal)
                if m:
                    markers.append(m)
                continue
            body = " ".join(l.strip() for l in lines)
            if standalone_start and standalone_end:
                removal = {"type": "lines", "start": _lineno(text, c.start), "end": _lineno(text, c.end - 1)}
            else:
                cut = line_start + len(before.rstrip()) if not standalone_start else c.start
                removal = {"type": "span", "line": _lineno(text, c.start), "text": text[cut:c.end]}
            m = _marker(path, text, c.start, body, removal)
            if m:
                markers.append(m)
            continue

        # A marker on its own line inside a larger block comment (JSDoc-style tag line).
        offset = inner_start
        for raw in inner.splitlines(keepends=True):
            pos = offset
            offset += len(raw)
            content = raw.rstrip("\n")
            if not _strip_doc(content).startswith("@claude"):
                continue
            ln_start, ln_end = _line_bounds(text, pos)
            if ln_start >= inner_start and ln_end <= inner_end:
                removal = {"type": "lines", "start": _lineno(text, pos), "end": _lineno(text, pos)}
            else:
                # Shares a line with the opener or closer: delete only the marker text.
                mstart = pos + content.index("@claude")
                removal = {"type": "span", "line": _lineno(text, pos),
                           "text": text[mstart:min(ln_end, inner_end)].rstrip()}
            marker_pos = pos + content.index("@claude")
            m = _marker(path, text, marker_pos, _strip_doc(content), removal)
            if m:
                markers.append(m)
    return markers


def apply_removal(text, marker):
    """Return text with one edit marker removed, exactly as the removal describes."""
    r = marker.removal
    if r["type"] == "lines":
        lines = text.splitlines(keepends=True)
        return "".join(lines[: r["start"] - 1] + lines[r["end"]:])
    lines = text.splitlines(keepends=True)
    idx = r["line"] - 1
    head = "".join(lines[:idx])
    rest = "".join(lines[idx:])
    assert r["text"] in rest, "removal span not found"
    return head + rest.replace(r["text"], "", 1)


def _git_files(base):
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "."],
            cwd=base, capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return [Path(base) / p for p in out.split("\0") if p]


def _walk(base):
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            yield Path(root) / f


def _read(path):
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def collect(paths):
    """(path, explicit) pairs to scan."""
    if not paths:
        paths, explicit_files = [Path(".")], False
    else:
        explicit_files = True
    for p in map(Path, paths):
        if p.is_file():
            yield p, explicit_files
        elif p.is_dir():
            files = _git_files(p)
            for f in files if files is not None else _walk(p):
                yield f, False


def scan(paths):
    markers, seen = [], set()
    for path, explicit in collect(paths):
        key = os.path.realpath(path)
        lang = lang_for(path)
        if key in seen or not lang or not path.is_file():
            continue
        seen.add(key)
        text = _read(path)
        if text is None or (not explicit and SKIP_PRAGMA in text):
            continue
        markers.extend(find_markers_in_text(text, lang, os.path.relpath(path)))
    return markers


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--json", action="store_true", help="one JSON object per marker")
    args = ap.parse_args(argv)
    for m in scan(args.paths):
        if args.json:
            print(json.dumps(m.as_dict()))
        else:
            flag = " (EMPTY: needs clarification)" if m.needs_clarification else ""
            print(f"{m.path}:{m.line}:{m.col} {m.kind}{flag}: {m.instruction}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
