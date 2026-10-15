"""The persona played by Claude Code (``claude -p``) with lyra-browser as its MCP server.

Uses whatever Claude Code is signed in as — a subscription, usually — so a
persona run costs no API key. The persona is the system prompt (replacing the
coding assistant's), the task is the prompt, the only tools are ours, and
nobody answers permission prompts: with ``--permission-prompts none`` an
elicitation from the server is cancelled, which the server reads as a refusal.
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
    last_json_object,
    offered_tool_names,
    run_process,
    write_mcp_config,
    write_prompts,
)

BIN_ENV = "LYRA_UAT_CLAUDE_BIN"


def find_claude() -> str | None:
    return os.environ.get(BIN_ENV) or shutil.which("claude")


class ClaudeCodeBrain(HarnessBrain):
    backend = "claude-code"

    def __init__(self, spec: BrainSpec) -> None:
        self.spec = spec
        self.model = spec.model

    def argv(
        self,
        binary: str,
        spec: RunSpec,
        *,
        mcp_config: Path,
        system_file: Path,
        task_prompt: str,
    ) -> list[str]:
        allowed = [f"mcp__{MCP_SERVER_NAME}__{name}" for name in offered_tool_names(spec)]
        argv = [
            binary,
            "-p",
            task_prompt,
            "--output-format",
            "json",
            "--mcp-config",
            str(mcp_config),
            "--strict-mcp-config",
            # No settings from anywhere: the operator's user settings carry their
            # reply language, default model and effort, hooks and plugins, and their
            # CLAUDE.md rides along. Measured with Claude Code 2.1.289: with them a
            # persona answered in Korean for an English persona and the first request
            # was 20,889 cache-creation tokens against 2,594 without. `--safe-mode`
            # would also drop `--mcp-config` servers (measured), `--bare` needs an API
            # key; an empty source list leaves auth and our MCP server alone.
            "--setting-sources",
            "",
            "--system-prompt-file",
            str(system_file),
            # No built-in tools: the persona reads screens, not files or shells.
            "--tools",
            "",
            "--permission-mode",
            "dontAsk",
            "--permission-prompts",
            "none",
            "--no-session-persistence",
            "--disable-slash-commands",
            "--max-turns",
            str(self.spec.max_turns),
            "--allowedTools",
            *allowed,
        ]
        if self.model:
            argv += ["--model", self.model]
        if self.spec.max_budget_usd is not None:
            argv += ["--max-budget-usd", f"{self.spec.max_budget_usd:g}"]
        if self.spec.effort:
            argv += ["--effort", self.spec.effort]
        for flag in self.spec.extra.get("argv", []):
            argv.append(str(flag))
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
        binary = find_claude()
        if not binary:
            raise BrainError(f"claude CLI not found; install Claude Code or set {BIN_ENV}")
        folder = harness_dir(run_dir)
        mcp_config = write_mcp_config(folder / "mcp.json", run_file)
        system_file, _task_file = write_prompts(folder, system_prompt, task_prompt)
        argv = self.argv(
            binary, spec, mcp_config=mcp_config, system_file=system_file, task_prompt=task_prompt
        )
        (folder / "argv.json").write_text(
            json.dumps(argv, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        # Auto memory would give the run a memory directory of its own, keyed by the
        # run's working directory: clutter in the operator's ~/.claude per persona.
        env = child_env(run_dir, {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"})
        result = await run_process(argv, cwd=folder / "cwd", env=env, log_dir=folder)
        return self.parse(result.stdout, result.exit_code, result.stderr)

    def parse(self, stdout: str, exit_code: int | None, stderr: str = "") -> BrainInfo:
        info = BrainInfo(backend=self.backend, model=self.model, exit_code=exit_code)
        payload: dict[str, Any] | None = last_json_object(stdout)
        if payload is None:
            tail = (stderr or stdout).strip().splitlines()
            info.error = (
                f"claude exited {exit_code} without a JSON result: {tail[-1] if tail else ''}"
            )
            return info
        usage = payload.get("usage") or {}
        info.turns = int(payload.get("num_turns") or 0)
        info.input_tokens = int(usage.get("input_tokens") or 0)
        info.output_tokens = int(usage.get("output_tokens") or 0)
        info.cache_read_tokens = int(usage.get("cache_read_input_tokens") or 0)
        info.cache_write_tokens = int(usage.get("cache_creation_input_tokens") or 0)
        cost = payload.get("total_cost_usd")
        info.cost_usd = float(cost) if isinstance(cost, int | float) else None
        session = payload.get("session_id")
        info.session_id = str(session) if session else None
        model_usage = payload.get("modelUsage")
        if isinstance(model_usage, dict) and model_usage and not info.model:
            info.model = ",".join(sorted(str(k) for k in model_usage))
        if payload.get("is_error"):
            info.error = str(payload.get("result") or "claude reported is_error")[:500]
        denials = payload.get("permission_denials") or []
        if denials and not info.error:
            info.error = f"{len(denials)} permission denial(s): " + ", ".join(
                str(d.get("tool_name", d)) for d in denials[:5]
            )
        return info
