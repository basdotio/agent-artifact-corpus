"""Windows implementation of the platform layer."""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

from .base import Platform

_HINTS = {
    "ctags": "Install Universal Ctags (`winget install UniversalCtags.Ctags` or `scoop bucket add extras; scoop install universal-ctags`). Note: `scoop install ctags` is the old Exuberant Ctags without JSON. Or run `scripts\\install.ps1`.",
    "rg": "Install ripgrep (`winget install BurntSushi.ripgrep.MSVC` or `scoop install ripgrep`), or run `scripts\\install.ps1`.",
    "global": "Install GNU Global (`scoop install global`), or run `scripts\\install.ps1`. Optional: without it StaticSight falls back to ripgrep.",
    "gtags": "Install GNU Global (`scoop install global`), or run `scripts\\install.ps1`. Optional: without it StaticSight falls back to ripgrep.",
    "cppcheck": "Install cppcheck (`winget install Cppcheck.Cppcheck` or `scoop install cppcheck`), or run `scripts\\install.ps1`.",
    "git": "Install Git for Windows (`winget install Git.Git`) and make sure the workspace is a git repository.",
}

# Only real executables: `.cmd`/`.bat` shims would need cmd.exe, which re-introduces shell quoting risks.
_EXTENSIONS = (".exe", ".com")
_CREATE_NEW_PROCESS_GROUP = 0x00000200
_CREATE_NO_WINDOW = 0x08000000


class WindowsPlatform(Platform):
    name = "windows"
    case_sensitive = False

    def find_executable(self, tool: str) -> str | None:
        names = [tool] if tool.lower().endswith(_EXTENSIONS) else [tool + ext for ext in _EXTENSIONS]
        for d in os.environ.get("PATH", "").split(os.pathsep):
            d = d.strip().strip('"')
            if not d:
                continue
            for n in names:
                cand = os.path.join(d, n)
                if os.path.isfile(cand):
                    return cand
        return None

    def spawn_kwargs(self) -> dict:
        return {"creationflags": _CREATE_NEW_PROCESS_GROUP | _CREATE_NO_WINDOW}

    def kill_tree(self, proc: asyncio.subprocess.Process) -> None:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                creationflags=_CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError):
            pass
        try:
            proc.kill()
        except (ProcessLookupError, OSError):
            pass

    def default_cache_dir(self) -> Path:
        base = os.environ.get("LOCALAPPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Local") / "staticsight"

    def install_hint(self, tool: str) -> str | None:
        return _HINTS.get(tool)

    def to_posix(self, path: str) -> str:
        p = path.replace("\\", "/")
        return p[2:] if p.startswith("./") else p
