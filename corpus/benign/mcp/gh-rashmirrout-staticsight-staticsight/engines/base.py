"""Common entry point for running an engine binary through the platform layer."""

from __future__ import annotations

import os
from typing import Mapping, Sequence

from ..core.errors import ToolMissing
from ..platform import CmdResult, current


def disabled_engines() -> set[str]:
    """Engines forced 'missing' via STATICSIGHT_DISABLE_ENGINES (comma list), e.g. to force the ripgrep fallback."""
    return {e.strip().lower() for e in os.environ.get("STATICSIGHT_DISABLE_ENGINES", "").split(",") if e.strip()}


def find_engine(tool: str) -> str | None:
    if tool.lower() in disabled_engines():
        return None
    return current().find_executable(tool)


def is_available(tool: str) -> bool:
    return find_engine(tool) is not None


async def run_engine(
    tool: str,
    args: Sequence[str],
    cwd: str | os.PathLike[str],
    timeout: float,
    env: Mapping[str, str] | None = None,
    stdin_data: str | None = None,
) -> CmdResult:
    """Run `tool args...` (no shell). Raises ToolMissing / ToolTimeout; non-zero exits are returned."""
    exe = find_engine(tool)
    if exe is None:
        raise ToolMissing(tool, current().install_hint(tool))
    try:
        return await current().run(exe, args, cwd, timeout, env=env, stdin_data=stdin_data, display_name=tool)
    except FileNotFoundError as exc:  # removed between lookup and spawn
        raise ToolMissing(tool, current().install_hint(tool)) from exc


def to_posix(path: str) -> str:
    return current().to_posix(path)
