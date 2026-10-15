"""What the harness brains share: a child process, its environment, its MCP server.

A harness (Claude Code, Codex) owns the agent loop. We give it the persona as
its prompt, ``lyra-browser --uat-run <run.json>`` as its MCP server, and the
run's tools by name; the server records everything the harness does. What
comes back is the process's output — turns, cost, session — for the report.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..procs import reap_group, spawn, stop_group
from ..spec import UAT_TOOLS, RunSpec

MCP_SERVER_NAME = "lyra"
GRACE_S = 10.0

# Environment of the parent that must not leak into a harness child: a nested
# Claude Code refuses to start inside another, and a harness must not inherit
# this session's identity.
_SCRUB_PREFIXES = ("CLAUDECODE", "CLAUDE_CODE_", "CODEX_")


@dataclass(slots=True)
class ProcessResult:
    argv: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    duration_s: float


def harness_dir(run_dir: Path) -> Path:
    """Where a harness's own files live: prompts, MCP config, logs, an empty cwd."""
    path = run_dir / "harness"
    (path / "cwd").mkdir(parents=True, exist_ok=True)
    return path


def child_env(run_dir: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(_SCRUB_PREFIXES)}
    env["LYRA_UAT_RUN_DIR"] = str(run_dir)
    if extra:
        env.update(extra)
    return env


def server_command(run_file: Path) -> tuple[str, list[str]]:
    """The MCP server a harness spawns: this interpreter, this package, this run."""
    return sys.executable, ["-m", "lyra_browser", "--uat-run", str(run_file)]


def write_mcp_config(path: Path, run_file: Path) -> Path:
    command, args = server_command(run_file)
    config = {"mcpServers": {MCP_SERVER_NAME: {"command": command, "args": args}}}
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def offered_tool_names(spec: RunSpec) -> list[str]:
    return [*spec.offered_tools(), *UAT_TOOLS]


def write_prompts(folder: Path, system_prompt: str, task_prompt: str) -> tuple[Path, Path]:
    system_file = folder / "system_prompt.md"
    task_file = folder / "task_prompt.md"
    system_file.write_text(system_prompt, encoding="utf-8")
    task_file.write_text(task_prompt, encoding="utf-8")
    return system_file, task_file


async def run_process(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log_dir: Path,
    stdin_text: str | None = None,
) -> ProcessResult:
    """Run the harness to completion. Cancelled (the runner's wall clock), the whole process
    group — the harness, its MCP server, the browser — is interrupted first so the harness
    can end its turn and close the server properly, then killed if it will not. After a
    normal exit whatever the harness left running is stopped too."""
    loop = asyncio.get_running_loop()
    started = loop.time()
    proc = await spawn(
        argv,
        cwd=str(cwd),
        env=env,
        stdin=asyncio.subprocess.PIPE if stdin_text is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await proc.communicate(
            input=stdin_text.encode("utf-8") if stdin_text is not None else None
        )
    except asyncio.CancelledError:
        # Shielded: a second cancellation must not leave a browser running on the profile.
        await asyncio.shield(stop_group(proc, grace_s=GRACE_S))
        raise
    await reap_group(proc.pid)
    stdout = out.decode("utf-8", errors="replace")
    stderr = err.decode("utf-8", errors="replace")
    (log_dir / "stdout.log").write_text(stdout, encoding="utf-8")
    (log_dir / "stderr.log").write_text(stderr, encoding="utf-8")
    return ProcessResult(
        argv=argv,
        exit_code=proc.returncode,
        stdout=stdout,
        stderr=stderr,
        duration_s=round(loop.time() - started, 1),
    )


def json_lines(text: str) -> list[dict[str, Any]]:
    """Every line of ``text`` that parses as a JSON object."""
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def last_json_object(text: str) -> dict[str, Any] | None:
    """The result object of a harness's output.

    ``claude -p --output-format json`` prints either one object or (measured
    with Claude Code 2.1.289) a JSON array of the session's messages ending in
    the ``result`` message; a stream prints one object per line. Whatever the
    shape, the ``result``-typed object wins, else the last object.
    """
    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        try:
            whole = json.loads(stripped)
        except ValueError:
            whole = None
        if isinstance(whole, dict):
            return whole
        if isinstance(whole, list):
            objects = [item for item in whole if isinstance(item, dict)]
            for item in reversed(objects):
                if item.get("type") == "result":
                    return item
            return objects[-1] if objects else None
    rows = json_lines(text)
    for row in reversed(rows):
        if row.get("type") == "result":
            return row
    return rows[-1] if rows else None
