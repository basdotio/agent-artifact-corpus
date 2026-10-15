"""The persona played by Codex (``codex exec``) with lyra-browser as its MCP server.

Codex reads its MCP servers from config, so the server is passed as ``-c``
overrides; the user's own config and rules are ignored so a run does not
inherit their servers. Codex has no system-prompt flag in exec mode, so the
role goes ahead of the task in the one prompt it gets. The shell sandbox is
read-only and approvals are off: what the persona can do is what our server
offers.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from ..report import BrainInfo
from ..spec import BrainSpec, RunSpec
from .base import BrainError, HarnessBrain
from .harness import (
    MCP_SERVER_NAME,
    child_env,
    harness_dir,
    json_lines,
    offered_tool_names,
    run_process,
    server_command,
    write_prompts,
)

BIN_ENV = "LYRA_UAT_CODEX_BIN"


def find_codex() -> str | None:
    return os.environ.get(BIN_ENV) or shutil.which("codex")


def _toml_string(value: str) -> str:
    return json.dumps(value)  # a JSON string is a valid TOML basic string


class CodexBrain(HarnessBrain):
    backend = "codex"

    def __init__(self, spec: BrainSpec) -> None:
        self.spec = spec
        self.model = spec.model

    def argv(
        self,
        binary: str,
        spec: RunSpec,
        *,
        run_file: Path,
        cwd: Path,
        last_message: Path,
        prompt: str,
    ) -> list[str]:
        command, args = server_command(run_file)
        server = f"mcp_servers.{MCP_SERVER_NAME}"
        argv = [
            binary,
            "exec",
            "--json",
            "-o",
            str(last_message),
            "--ephemeral",
            "--skip-git-repo-check",
            "--ignore-user-config",
            "--ignore-rules",
            # A misspelt override key is an error, not a silently ignored setting
            # (measured: `-c mcp_servers.x.bogus=1` is refused under this flag).
            "--strict-config",
            "--sandbox",
            "read-only",
            "-C",
            str(cwd),
            "-c",
            'approval_policy="never"',
            "-c",
            f"{server}.command={_toml_string(command)}",
            "-c",
            f"{server}.args={json.dumps(args)}",
            "-c",
            f"{server}.startup_timeout_sec=90",
            "-c",
            f"{server}.tool_timeout_sec=120",
            # Only the tools this persona is offered, pre-approved: with approvals off Codex
            # refuses every MCP call that needs one (measured, "approval policy is never"),
            # and nobody is there to answer. What the persona may do is decided by our
            # server's guards and budget, and by the read-only sandbox around its shell.
            "-c",
            f"{server}.enabled_tools={json.dumps(offered_tool_names(spec))}",
            "-c",
            f'{server}.default_tools_approval_mode="approve"',
        ]
        if self.model:
            argv += ["-m", self.model]
        for flag in self.spec.extra.get("argv", []):
            argv.append(str(flag))
        argv.append(prompt)
        return argv

    async def run(
        self,
        spec: RunSpec,
        run_dir: Path,
        run_file: Path,
        *,
        system_prompt: str,
        task_prompt: str,
    ) -> BrainInfo:
        binary = find_codex()
        if not binary:
            raise BrainError(f"codex CLI not found; install Codex or set {BIN_ENV}")
        folder = harness_dir(run_dir)
        write_prompts(folder, system_prompt, task_prompt)
        prompt = f"{system_prompt.rstrip()}\n\n---\n\n{task_prompt}"
        last_message = folder / "last_message.md"
        argv = self.argv(
            binary,
            spec,
            run_file=run_file,
            cwd=folder / "cwd",
            last_message=last_message,
            prompt=prompt,
        )
        (folder / "argv.json").write_text(
            json.dumps(argv, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        result = await run_process(argv, cwd=folder / "cwd", env=child_env(run_dir), log_dir=folder)
        return self.parse(result.stdout, result.exit_code, result.stderr)

    def parse(self, stdout: str, exit_code: int | None, stderr: str = "") -> BrainInfo:
        info = BrainInfo(backend=self.backend, model=self.model, exit_code=exit_code)
        events = json_lines(stdout)
        turns = 0
        for event in events:
            kind = str(event.get("type", ""))
            if kind.endswith("turn.completed") or kind == "turn_complete":
                turns += 1
            usage = _find_usage(event)
            if usage:
                info.input_tokens = int(usage.get("input_tokens") or info.input_tokens)
                info.output_tokens = int(usage.get("output_tokens") or info.output_tokens)
                cached = usage.get("cached_input_tokens", usage.get("cache_read_input_tokens"))
                if cached is not None:
                    info.cache_read_tokens = int(cached or 0)
            session = event.get("thread_id") or event.get("session_id")
            if session and not info.session_id:
                info.session_id = str(session)
        info.turns = turns
        if exit_code not in (None, 0):
            tail = stderr.strip().splitlines()
            info.error = f"codex exited {exit_code}: {tail[-1] if tail else ''}"[:500]
        elif not events:
            info.error = "codex produced no JSON events"
        return info


def _find_usage(event: dict[str, Any]) -> dict[str, Any] | None:
    """Codex's usage object sits at different depths depending on the event."""
    for key in ("usage", "token_usage"):
        value = event.get(key)
        if isinstance(value, dict):
            return value
    for key in ("payload", "msg", "item", "info"):
        nested = event.get(key)
        if isinstance(nested, dict):
            found = _find_usage(nested)
            if found:
                return found
    return None
