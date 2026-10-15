from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return (self.stdout + "\n" + self.stderr).strip()


class CommandRunner(Protocol):
    def resolve(self, executable: str) -> str: ...

    def run(
        self,
        executable: str,
        args: list[str],
        stdin: str | None = None,
        timeout: float = 60,
    ) -> CommandResult: ...
