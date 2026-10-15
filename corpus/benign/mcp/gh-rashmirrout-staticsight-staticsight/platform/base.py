"""Platform interface. This package is the ONLY place in StaticSight that knows which OS it runs on.

Everything above it (engines/, tools/) works with POSIX-style workspace-relative paths and calls `run()`.
"""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Mapping, Sequence

from ..core.errors import StaticSightError, ToolTimeout

MAX_STDOUT_BYTES = 8 * 1024 * 1024
MAX_STDERR_BYTES = 64 * 1024


@dataclass
class CmdResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    truncated: bool = False


class Platform(ABC):
    name: str = "base"
    case_sensitive: bool = True

    # ------------------------------------------------------------------ OS hooks
    @abstractmethod
    def find_executable(self, tool: str) -> str | None:
        """Absolute path of a runnable executable for `tool`, or None."""

    @abstractmethod
    def spawn_kwargs(self) -> dict:
        """Extra kwargs for asyncio.create_subprocess_exec (process group, hidden window, ...)."""

    @abstractmethod
    def kill_tree(self, proc: asyncio.subprocess.Process) -> None:
        """Forcefully terminate a process and all of its children."""

    @abstractmethod
    def default_cache_dir(self) -> Path:
        """Per-user cache directory for StaticSight data (GNU Global databases)."""

    @abstractmethod
    def install_hint(self, tool: str) -> str | None:
        """How to install `tool` on this OS."""

    @abstractmethod
    def to_posix(self, path: str) -> str:
        """Convert a path printed by a native tool into StaticSight's internal '/'-separated form."""

    # ------------------------------------------------------------- shared logic
    def path_key(self, path: str) -> str:
        """Key for comparing/deduplicating paths (case-folded on case-insensitive file systems)."""
        p = self.to_posix(path)
        return p if self.case_sensitive else p.casefold()

    def same_path(self, a: str, b: str) -> bool:
        return self.path_key(a) == self.path_key(b)

    def fnmatch(self, name: str, pattern: str) -> bool:
        if self.case_sensitive:
            return fnmatchcase(name, pattern)
        return fnmatchcase(name.casefold(), pattern.casefold())

    async def run(
        self,
        exe: str,
        args: Sequence[str],
        cwd: str | os.PathLike[str],
        timeout: float,
        env: Mapping[str, str] | None = None,
        stdin_data: str | None = None,
        max_bytes: int = MAX_STDOUT_BYTES,
        display_name: str = "",
    ) -> CmdResult:
        """Run `exe args...` without a shell. Non-zero exit codes are returned, not raised."""
        name = display_name or os.path.basename(exe)
        argv = [exe, *[str(a) for a in args]]
        full_env = dict(os.environ)
        if env:
            full_env.update(env)
        if not os.path.isdir(cwd):
            raise StaticSightError(f"Working directory `{cwd}` does not exist.")
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(cwd),
            env=full_env,
            stdin=asyncio.subprocess.PIPE if stdin_data is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **self.spawn_kwargs(),
        )
        truncated = False

        async def read_stream(stream: asyncio.StreamReader, cap: int, is_stdout: bool) -> bytes:
            nonlocal truncated
            chunks: list[bytes] = []
            size = 0
            while True:
                chunk = await stream.read(65536)
                if not chunk:
                    break
                if size < cap:
                    chunks.append(chunk[: cap - size])
                size += len(chunk)
                if size >= cap and is_stdout:
                    truncated = True
                    self.kill_tree(proc)
                    break
            return b"".join(chunks)

        async def feed_stdin() -> None:
            if stdin_data is None or proc.stdin is None:
                return
            try:
                proc.stdin.write(stdin_data.encode("utf-8", errors="replace"))
                await proc.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                try:
                    proc.stdin.close()
                except Exception:
                    pass

        assert proc.stdout is not None and proc.stderr is not None
        try:
            _, out, err = await asyncio.wait_for(
                asyncio.gather(
                    feed_stdin(),
                    read_stream(proc.stdout, max_bytes, True),
                    read_stream(proc.stderr, MAX_STDERR_BYTES, False),
                ),
                timeout=timeout,
            )
            rc = await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError as exc:
            self.kill_tree(proc)
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                pass
            raise ToolTimeout(
                f"`{name}` did not finish within {timeout:g}s.",
                "Narrow the query (path_glob / file_path) or raise STATICSIGHT_TIMEOUT.",
            ) from exc
        return CmdResult(
            argv=argv,
            returncode=rc if not truncated else 0,
            stdout=out.decode("utf-8", errors="replace"),
            stderr=err.decode("utf-8", errors="replace"),
            truncated=truncated,
        )
