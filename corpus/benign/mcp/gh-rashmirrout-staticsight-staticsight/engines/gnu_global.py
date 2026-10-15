"""GNU Global adapter: database build/update and `global -x` queries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..config import Config
from ..core.errors import StaticSightError
from ..platform import CmdResult
from .base import is_available, run_engine, to_posix

GLOBAL_LINE = re.compile(r"^(\S+)\s+(\d+)\s+(\S+)\s?(.*)$")
INDEX_TIMEOUT_S = 1800


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    text: str


def available() -> bool:
    return is_available("gtags") and is_available("global")


def parse_x_output(stdout: str) -> list[Hit]:
    hits = []
    for raw in stdout.splitlines():
        m = GLOBAL_LINE.match(raw.rstrip("\r"))
        if m:
            hits.append(Hit(to_posix(m.group(3)), int(m.group(2)), m.group(4)))
    return sorted(set(hits), key=lambda h: (h.path, h.line))


async def query(cfg: Config, env: dict[str, str], flag: str, symbol: str) -> list[Hit] | None:
    """`global <flag> -- symbol`; None when the query cannot be answered (caller falls back)."""
    try:
        res = await run_engine("global", [flag, "--", symbol], cwd=cfg.workspace_root, timeout=cfg.timeout_s, env=env)
    except StaticSightError:
        return None
    if res.returncode not in (0, 1):
        return None
    return parse_x_output(res.stdout)


async def update_in_place(root: Path, env: dict[str, str]) -> CmdResult:
    """Incremental update of an existing in-repo GTAGS database."""
    return await run_engine("global", ["-u"], cwd=root, timeout=INDEX_TIMEOUT_S, env=env)


async def build(root: Path, db_path: Path, env: dict[str, str], files: list[str], incremental: bool) -> tuple[CmdResult, str]:
    """(Re)build the database from an explicit file list (fed on stdin). Returns (result, human-readable action)."""
    in_repo = db_path == root
    args = ["-i", "-f", "-"] if incremental or in_repo else ["-f", "-"]
    if not in_repo:
        args.append(str(db_path))
    res = await run_engine("gtags", args, cwd=root, timeout=INDEX_TIMEOUT_S, env=env, stdin_data="\n".join(files) + "\n")
    action = " ".join(["gtags", *args][:4]) + f" ({len(files)} files)"
    return res, action
