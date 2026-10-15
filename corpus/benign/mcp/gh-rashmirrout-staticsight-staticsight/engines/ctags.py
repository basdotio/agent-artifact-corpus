"""Universal Ctags JSON runner with an mtime-keyed cache, plus scope lookup helpers."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from ..config import Config
from ..core.errors import StaticSightError, ToolFailed
from .base import run_engine, to_posix
from .capabilities import ensure_ctags

BLOCK_KINDS = frozenset({"function", "class", "struct", "union", "enum", "namespace", "macro"})
FUNCTION_KINDS = frozenset({"function"})
TYPE_KINDS = frozenset({"class", "struct", "union", "enum"})
DEFINITION_KINDS = frozenset({"function", "class", "struct", "union", "enum", "macro", "typedef", "namespace", "variable", "member"})
_KIND_PRIORITY = {"function": 0, "struct": 1, "class": 1, "union": 1, "enum": 2, "macro": 3, "namespace": 4}

CTAGS_ARGS = [
    "--output-format=json",
    "--fields=+neKSZ",
    "--kinds-C++=+p",
    "--sort=no",
    "--language-force=C++",
    "-f",
    "-",
]
# Language auto-detection (any of the ~150 languages Universal Ctags knows); used by the semantic chunker.
CTAGS_GENERIC_ARGS = ["--output-format=json", "--fields=+neKSZ", "--sort=no", "-f", "-"]


@dataclass(frozen=True)
class Tag:
    name: str
    kind: str
    line: int
    end: int
    path: str
    scope: str = ""
    scope_kind: str = ""
    signature: str = ""
    typeref: str = ""
    pattern: str = ""

    @property
    def qualified(self) -> str:
        if not self.scope or "::" in self.name:
            return self.name
        return f"{self.scope}::{self.name}"

    @property
    def short_name(self) -> str:
        return self.name.rsplit("::", 1)[-1]

    @property
    def return_type(self) -> str:
        t = self.typeref
        if t.startswith("typename:"):
            t = t[len("typename:"):]
        return t

    @property
    def display_signature(self) -> str:
        rt = self.return_type
        sig = self.signature if self.kind in ("function", "prototype", "macro") else ""
        base = f"{self.qualified}{sig}"
        return f"{rt} {base}".strip() if rt else base


_cache: dict[str, tuple[int, int, list[Tag]]] = {}
_ANON = re.compile(r"__anon[0-9a-f]+")


def _anon(text: str) -> str:
    """ctags names anonymous namespaces/structs with a per-run hash; normalise so runs are comparable."""
    return _ANON.sub("(anonymous)", text)


def _parse(stdout: str) -> dict[str, list[Tag]]:
    by_path: dict[str, list[Tag]] = {}
    for raw in stdout.splitlines():
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if d.get("_type") != "tag" or not isinstance(d.get("line"), int):
            continue
        path = to_posix(str(d.get("path", "")))
        line = d["line"]
        end = d.get("end") if isinstance(d.get("end"), int) else line
        by_path.setdefault(path, []).append(
            Tag(
                name=_anon(str(d.get("name", ""))),
                kind=str(d.get("kind", "")),
                line=line,
                end=max(end, line),
                path=path,
                scope=_anon(str(d.get("scope", ""))),
                scope_kind=str(d.get("scopeKind", "")),
                signature=str(d.get("signature", "")),
                typeref=str(d.get("typeref", "")),
                pattern=str(d.get("pattern", "")),
            )
        )
    return by_path


def _arg(rel: str) -> str:
    return "./" + rel if rel.startswith("-") else rel


async def ctags_for_files(cfg: Config, rel_paths: Sequence[str], generic: bool = False) -> dict[str, list[Tag]]:
    """Return tags per workspace-relative path (missing/unreadable files map to []).

    generic=False parses every file as C++ (the review tools); generic=True lets ctags detect each file's language.
    """
    args = CTAGS_GENERIC_ARGS if generic else CTAGS_ARGS
    mode = "g:" if generic else "c:"
    result: dict[str, list[Tag]] = {}
    todo: list[str] = []
    stats: dict[str, tuple[int, int]] = {}
    for rel in dict.fromkeys(rel_paths):
        try:
            st = os.stat(cfg.workspace_root / rel)
        except OSError:
            result[rel] = []
            continue
        key = mode + str(cfg.workspace_root / rel)
        stats[rel] = (st.st_mtime_ns, st.st_size)
        cached = _cache.get(key)
        if cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
            result[rel] = cached[2]
        else:
            todo.append(rel)
    if todo:
        await ensure_ctags()
    for i in range(0, len(todo), 200):
        batch = todo[i : i + 200]
        res = await run_engine("ctags", args + [_arg(r) for r in batch], cwd=cfg.workspace_root, timeout=cfg.timeout_s)
        if res.returncode != 0 and not res.stdout.strip():
            if "json" in res.stderr.lower():
                raise ToolFailed(
                    "`ctags` does not support `--output-format=json`.",
                    "Install Universal Ctags built with libjansson (Exuberant Ctags is not supported).",
                )
            raise ToolFailed(f"`ctags` failed: {res.stderr.strip()[:300]}")
        parsed = _parse(res.stdout)
        for rel in batch:
            tags = parsed.get(rel, [])
            result[rel] = tags
            mt, sz = stats[rel]
            _cache[mode + str(cfg.workspace_root / rel)] = (mt, sz, tags)
    return result


async def ctags_for_file(cfg: Config, rel_path: str) -> list[Tag]:
    return (await ctags_for_files(cfg, [rel_path])).get(rel_path, [])


async def ctags_for_temp(cfg: Config, abs_path: Path, logical_path: str) -> list[Tag]:
    """Run ctags on a file outside the workspace (e.g. an old git blob) and relabel its path."""
    await ensure_ctags()
    res = await run_engine("ctags", CTAGS_ARGS + [str(abs_path)], cwd=abs_path.parent, timeout=cfg.timeout_s)
    tags = [t for ts in _parse(res.stdout).values() for t in ts]
    return [Tag(**{**t.__dict__, "path": logical_path}) for t in tags]


async def try_ctags_for_files(cfg: Config, rel_paths: Sequence[str], generic: bool = False) -> dict[str, list[Tag]]:
    """Best-effort variant used for enrichment: returns {} when ctags is unavailable."""
    try:
        return await ctags_for_files(cfg, rel_paths, generic=generic)
    except StaticSightError:
        return {}


def _scope_sort_key(t: Tag) -> tuple:
    return (t.end - t.line, -t.line, _KIND_PRIORITY.get(t.kind, 9), t.name)


def innermost(tags: Iterable[Tag], line: int, kinds: frozenset[str] = BLOCK_KINDS) -> Tag | None:
    cands = [t for t in tags if t.kind in kinds and t.line <= line <= t.end]
    if not cands:
        return None
    return min(cands, key=_scope_sort_key)


def enclosing_chain(tags: Iterable[Tag], line: int, kinds: frozenset[str] = BLOCK_KINDS) -> list[Tag]:
    """All scopes containing `line`, innermost first."""
    cands = [t for t in tags if t.kind in kinds and t.line <= line <= t.end]
    return sorted(cands, key=_scope_sort_key)


def dedupe(tags: Iterable[Tag]) -> list[Tag]:
    seen: set[tuple] = set()
    out = []
    for t in tags:
        key = (t.path, t.line, t.kind, t.qualified)
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def clear_cache() -> None:
    _cache.clear()
