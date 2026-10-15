"""ripgrep runner: always uses --json and parses the event stream natively."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Sequence

from ..config import CPP_GLOBS, Config
from ..core.errors import ToolFailed
from .base import run_engine, to_posix


@dataclass(frozen=True)
class RgLine:
    path: str
    line: int
    text: str
    is_match: bool


@dataclass
class RgResult:
    files: dict[str, list[RgLine]] = field(default_factory=dict)
    truncated: bool = False

    def matches(self) -> list[RgLine]:
        out = [ln for path in sorted(self.files) for ln in self.files[path] if ln.is_match]
        return out

    def window(self, path: str, line: int, radius: int) -> list[RgLine]:
        return [ln for ln in self.files.get(path, []) if abs(ln.line - line) <= radius]


def _glob_args(cfg: Config, globs: Sequence[str]) -> list[str]:
    args: list[str] = []
    for g in globs:
        args += ["-g", g]
    for ex in cfg.excludes:
        args += ["-g", "!" + ex]
    return args


def _text(obj: dict) -> str:
    if "text" in obj:
        return obj["text"]
    return ""


async def rg_search(
    cfg: Config,
    pattern: str | Sequence[str],
    *,
    word: bool = False,
    fixed: bool = False,
    ignore_case: bool = False,
    context: int = 0,
    globs: Sequence[str] = CPP_GLOBS,
    paths: Sequence[str] = (),
    max_count: int = 0,
) -> RgResult:
    argv = ["--json", "--no-config", "--no-messages", "--path-separator", "/"]
    if word:
        argv.append("-w")
    if fixed:
        argv.append("-F")
    if ignore_case:
        argv.append("-i")
    if context:
        argv += ["-C", str(context)]
    if max_count:
        argv += ["-m", str(max_count)]
    argv += _glob_args(cfg, globs)
    for p in [pattern] if isinstance(pattern, str) else pattern:
        argv += ["-e", p]
    argv.append("--")
    argv += list(paths) if paths else ["."]
    res = await run_engine("rg", argv, cwd=cfg.workspace_root, timeout=cfg.timeout_s)
    if res.returncode == 2 and not res.stdout.strip():
        raise ToolFailed(f"`rg` failed: {res.stderr.strip()[:300]}", "Check the pattern / path arguments.")
    out = RgResult(truncated=res.truncated)
    for raw in res.stdout.splitlines():
        if not raw.startswith("{"):
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        typ = ev.get("type")
        if typ not in ("match", "context"):
            continue
        data = ev.get("data", {})
        path = _text(data.get("path", {}))
        if not path:
            continue
        path = to_posix(path)
        text = _text(data.get("lines", {})).rstrip("\n").rstrip("\r")
        num = data.get("line_number")
        if not isinstance(num, int):
            continue
        out.files.setdefault(path, []).append(RgLine(path, num, text, typ == "match"))
    for path in out.files:
        out.files[path].sort(key=lambda ln: ln.line)
    return out


async def rg_files(cfg: Config, globs: Sequence[str] = CPP_GLOBS) -> list[str]:
    argv = ["--files", "--no-config", "--no-messages", "--path-separator", "/"] + _glob_args(cfg, globs)
    res = await run_engine("rg", argv, cwd=cfg.workspace_root, timeout=cfg.timeout_s)
    files = [to_posix(ln) for ln in res.stdout.splitlines() if ln.strip()]
    return sorted(files)
