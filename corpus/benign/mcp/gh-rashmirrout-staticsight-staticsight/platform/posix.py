"""Linux / macOS implementation of the platform layer."""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
from pathlib import Path

from .base import Platform

_HINTS = {
    "ctags": "Install Universal Ctags >= 5.9 with JSON support (`apt-get install universal-ctags`, `tdnf install ctags`, `brew install universal-ctags`), or run `scripts/install.sh`.",
    "rg": "Install ripgrep (`apt-get install ripgrep`, `tdnf install ripgrep`, `brew install ripgrep`), or run `scripts/install.sh`.",
    "global": "Install GNU Global (`apt-get install global`, `brew install global`, or build from https://www.gnu.org/software/global/), or run `scripts/install.sh`.",
    "gtags": "Install GNU Global (`apt-get install global`, `brew install global`, or build from https://www.gnu.org/software/global/), or run `scripts/install.sh`.",
    "cppcheck": "Install cppcheck (`apt-get install cppcheck`, `tdnf install cppcheck`, `brew install cppcheck`), or run `scripts/install.sh`.",
    "git": "Install git and make sure the workspace is a git repository.",
}


class PosixPlatform(Platform):
    name = "posix"
    case_sensitive = True

    def find_executable(self, tool: str) -> str | None:
        return shutil.which(tool)

    def spawn_kwargs(self) -> dict:
        return {"start_new_session": True}  # own process group so kill_tree reaches grandchildren

    def kill_tree(self, proc: asyncio.subprocess.Process) -> None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except ProcessLookupError:
                pass

    def default_cache_dir(self) -> Path:
        xdg = os.environ.get("XDG_CACHE_HOME")
        return (Path(xdg) if xdg else Path.home() / ".cache") / "staticsight"

    def install_hint(self, tool: str) -> str | None:
        return _HINTS.get(tool)

    def to_posix(self, path: str) -> str:
        # A backslash is a legal file-name character on POSIX, so paths are returned unchanged.
        return path[2:] if path.startswith("./") else path
