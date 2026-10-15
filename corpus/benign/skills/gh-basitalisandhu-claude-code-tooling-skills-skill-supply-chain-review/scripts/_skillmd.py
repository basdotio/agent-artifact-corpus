"""_skillmd.py: a small, strict reader for SKILL.md front matter. Standard library only.

Byte-identical copies sit in the scripts folder of every skill in this plugin that reads front matter, so each skill
still works when it is copied on its own; tests/test_skillmd_helper.py checks the copies match.

It understands the subset of YAML that skill front matter uses: top-level `key: value` lines; values that are plain,
double-quoted (with backslash escapes) or single-quoted; `|` and `>` block scalars; `[a, b]` flow lists; `- item` block
lists; and one level of nested `key: value` mappings (such as `metadata:`). Anything a strict YAML reader would reject
in that subset is returned as a problem with its line number rather than guessed at.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

KEY_RE = re.compile(r"^([A-Za-z_][\w.-]*):(?:[ \t]+(.*?))?[ \t]*$")
NESTED_RE = re.compile(r"^([ \t]+)(?:- )?([A-Za-z_][\w.-]*):(?:[ \t]+(.*?))?[ \t]*$")
INDICATORS = "&*!%@`,]}?#|>"
ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/", "0": "\0", "r": "\r", " ": " "}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache", ".ruff_cache"}


@dataclass
class Scalar:
    key: str
    value: object
    style: str
    line: int
    raw: str = ""


@dataclass
class FrontMatter:
    present: bool = False
    closed: bool = False
    fields: dict[str, Scalar] = field(default_factory=dict)
    problems: list[tuple[int, str]] = field(default_factory=list)
    body_start: int = 0
    end_line: int = 0

    def text(self, key: str) -> str:
        s = self.fields.get(key)
        return s.value if s is not None and isinstance(s.value, str) else ""


def decode_double(raw: str) -> tuple[str, bool]:
    """Decode a double-quoted YAML scalar that starts at raw[0]. Returns (value, closed and nothing but a comment
    after it)."""
    out, i = [], 1
    while i < len(raw):
        c = raw[i]
        if c == "\\" and i + 1 < len(raw):
            n = raw[i + 1]
            if n == "u" and re.fullmatch(r"[0-9a-fA-F]{4}", raw[i + 2 : i + 6] or ""):
                out.append(chr(int(raw[i + 2 : i + 6], 16)))
                i += 6
                continue
            out.append(ESCAPES.get(n, n))
            i += 2
            continue
        if c == '"':
            rest = raw[i + 1 :].strip()
            return "".join(out), rest == "" or rest.startswith("#")
        out.append(c)
        i += 1
    return "".join(out), False


def decode_single(raw: str) -> tuple[str, bool]:
    out, i = [], 1
    while i < len(raw):
        if raw[i] == "'":
            if raw[i + 1 : i + 2] == "'":
                out.append("'")
                i += 2
                continue
            rest = raw[i + 1 :].strip()
            return "".join(out), rest == "" or rest.startswith("#")
        out.append(raw[i])
        i += 1
    return "".join(out), False


def encode_double(value: str) -> str:
    """Render text as one double-quoted YAML scalar; newlines and tabs become single spaces."""
    flat = re.sub(r"\s+", " ", value).strip()
    return '"' + flat.replace("\\", "\\\\").replace('"', '\\"') + '"'


def scalar(raw: str, line: int, key: str, problems: list[tuple[int, str]]) -> tuple[object, str]:
    """Parse one inline value. Returns (value, style)."""
    if raw == "":
        return "", "empty"
    if raw[0] == '"':
        value, ok = decode_double(raw)
        if not ok:
            problems.append((line, f"double-quoted value for '{key}' is not closed on its line"))
        return value, "double"
    if raw[0] == "'":
        value, ok = decode_single(raw)
        if not ok:
            problems.append((line, f"single-quoted value for '{key}' is not closed on its line"))
        return value, "single"
    if raw[0] == "[":
        if not raw.rstrip().endswith("]"):
            problems.append((line, f"flow list for '{key}' is not closed on its line"))
        items = [p.strip().strip("\"'") for p in raw.strip()[1:].rstrip("]").split(",")]
        return [p for p in items if p], "list"
    if raw[0] == "{":
        problems.append((line, f"flow mapping for '{key}' is not supported here; use indented lines"))
        return raw, "plain"
    value = re.split(r"\s+#", raw, maxsplit=1)[0].strip()
    if raw[0] in INDICATORS or raw[:2] in ("- ", ": ") or raw == "-":
        problems.append((line, f"plain value for '{key}' starts with a YAML indicator; wrap it in double quotes"))
    elif ": " in raw or " #" in raw or raw.endswith(":"):
        problems.append((line, f"plain value for '{key}' contains ': ' or ' #'; wrap it in double quotes"))
    return value, "plain"


def block(lines: list[str], style: str) -> str:
    """Join the lines of a | or > block scalar (indentation already known to be deeper than the key)."""
    texts = [ln for ln in lines]
    indent = min((len(t) - len(t.lstrip()) for t in texts if t.strip()), default=0)
    body = [t[indent:] if t.strip() else "" for t in texts]
    while body and not body[-1]:
        body.pop()
    if style.startswith("|"):
        return "\n".join(body)
    paragraphs, cur = [], []
    for t in body:
        if t:
            cur.append(t.strip())
        else:
            paragraphs.append(" ".join(cur))
            cur = []
    paragraphs.append(" ".join(cur))
    return "\n".join(p for p in paragraphs if p)


def parse(text: str) -> FrontMatter:
    """Read the front matter block at the top of a SKILL.md text."""
    fm = FrontMatter()
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return fm
    fm.present = True
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        fm.problems.append((1, "front matter opened with --- but never closed"))
        return fm
    fm.closed, fm.body_start, fm.end_line = True, end + 1, end + 1
    i = 1
    while i < end:
        line, number = lines[i], i + 1
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line[0] in " \t":
            fm.problems.append((number, "indented line outside a mapping or list"))
            i += 1
            continue
        m = KEY_RE.match(line)
        if not m:
            fm.problems.append((number, "line is not a 'key: value' pair"))
            i += 1
            continue
        key, raw = m.group(1), (m.group(2) or "")
        if key in fm.fields:
            fm.problems.append((number, f"duplicate key '{key}'"))
        j = i + 1
        while j < end and (not lines[j].strip() or lines[j][0] in " \t"):
            j += 1
        child = lines[i + 1 : j]
        if any(c.startswith("\t") or re.match(r"^ *\t", c) for c in child if c.strip()):
            fm.problems.append((number, f"tab used for indentation under '{key}'"))
        if raw[:1] in ("|", ">") and re.fullmatch(r"[|>][+-]?[1-9]?|[|>][1-9]?[+-]?", raw):
            fm.fields[key] = Scalar(key, block(child, raw), "block", number, raw)
        elif raw == "" and any(c.strip() for c in child):
            items = [c.strip() for c in child if c.strip()]
            if all(c.startswith("- ") or c == "-" for c in items):
                vals = []
                for k, c in enumerate(child):
                    if c.strip():
                        v, _ = scalar(c.strip()[2:].strip(), i + 2 + k, key, fm.problems)
                        vals.append(v if isinstance(v, str) else str(v))
                fm.fields[key] = Scalar(key, vals, "list", number, raw)
            else:
                mapping: dict[str, object] = {}
                for k, c in enumerate(child):
                    if not c.strip() or c.lstrip().startswith("#"):
                        continue
                    nm = NESTED_RE.match(c)
                    if not nm:
                        fm.problems.append((i + 2 + k, f"nested line under '{key}' is not 'key: value'"))
                        continue
                    v, _ = scalar(nm.group(3) or "", i + 2 + k, nm.group(2), fm.problems)
                    mapping[nm.group(2)] = v
                fm.fields[key] = Scalar(key, mapping, "map", number, raw)
        else:
            if any(c.strip() for c in child):
                fm.problems.append((number, f"value for '{key}' continues on indented lines; keep it on one line"))
            value, style = scalar(raw, number, key, fm.problems)
            fm.fields[key] = Scalar(key, value, style, number, raw)
        i = j
    return fm


def quoted_phrases(text: str) -> list[str]:
    """Phrases in straight or curly double quotes, as a user would type them."""
    found = re.findall(r'"([^"\n]{2,160})"', text) + re.findall("“([^”\n]{2,160})”", text)
    return [f.strip() for f in found if f.strip()]


def find_skill_files(paths: list[Path]) -> list[Path]:
    """SKILL.md files named directly, inside the given folders, or anywhere below them."""
    out: set[Path] = set()
    for p in paths:
        if p.is_file():
            out.add(p)
        elif p.is_dir():
            if (p / "SKILL.md").is_file():
                out.add(p / "SKILL.md")
                continue
            for f in p.rglob("SKILL.md"):
                if not SKIP_DIRS & set(f.relative_to(p).parts):
                    out.add(f)
    return sorted(out)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")
