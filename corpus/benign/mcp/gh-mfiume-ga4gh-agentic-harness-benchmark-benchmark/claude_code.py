"""Claude through Claude Code's headless mode (``claude -p``), billed to a Claude subscription.

Claude Code runs its own agent loop, so a task is run turn by turn as ``claude -p`` processes
rather than through the runner's model -> tools loop. What is kept identical to the other models:

- the system prompt (prompts/system.md replaces Claude Code's default one);
- the GA4GH MCP server, started through mcp_launch with the same HTTP cassette and sources;
- the final answer, a typed submit_answer call (served by submit_server), graded the same way;
- one reminder when a turn ends without a submission, and the step limit (as --max-turns).

Isolation: no built-in tools (no shell, files or web), only the two MCP servers, no setting
sources (so no CLAUDE.md and no memory index is loaded), a working directory of its own, and
sessions kept only to resume multi-turn tasks. The account's email address is still visible to
the model; no tool can read anything else on the machine.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from . import answer

MODELS = {"sonnet": "claude-sonnet-5", "opus": "claude-opus-5-5"}
SUBMIT_TOOL = "mcp__bench__submit_answer"
NUDGE = f"Call {SUBMIT_TOOL} with your final answer."
WORKDIR = Path(tempfile.gettempdir()) / "ga4gh-bench-claude-code"
_LIMIT = ("usage limit", "rate limit", "limit reached", "overloaded", "Not logged in")


class SubscriptionLimit(RuntimeError):
    """Claude Code refused to run (usage limit, login): the framework's to retry, not a model failure."""


class ClaudeCodeModel:
    def __init__(self, name: str, *, effort: str | None = None, seed: int | None = None, **_: Any) -> None:
        self.name = MODELS.get(name, name)
        self.effort, self.seed = effort, seed
        self.server: dict[str, Any] | None = None  # set by the runner: how to start the GA4GH MCP server

    def describe(self) -> dict[str, Any]:
        return {"provider": "claude-code", "model": self.name, "effort": self.effort,
                "claude_code": _version(), "seed": None, "temperature": None,
                "note": "seed and temperature are not settable through Claude Code"}

    async def run_task(self, task: dict[str, Any], system: str, max_steps: int, grade: Any) -> dict[str, Any]:
        WORKDIR.mkdir(exist_ok=True)
        session: str | None = None
        turns_out = []
        with tempfile.TemporaryDirectory(prefix="turns-", dir=WORKDIR) as tmp:
            for index, turn in enumerate(task["turns"]):
                out = Path(tmp) / f"submitted-{index}.json"
                config = Path(tmp) / f"mcp-{index}.json"
                config.write_text(json.dumps({"mcpServers": {
                    "ga4gh": {"command": self.server["command"], "args": self.server["args"], "env": self.server["env"]},
                    "bench": {"command": self.server["bench_python"], "args": ["-m", "benchmark.submit_server"],
                              "env": {**self.server["bench_env"], "BENCH_SUBMIT_TURN": json.dumps(turn),
                                      "BENCH_SUBMIT_OUT": str(out)}},
                }}))
                record = {"prompt": turn["prompt"], "tool_calls": [], "replies": [], "thinking": [],
                          "usage": {"prompt_tokens": 0, "completion_tokens": 0, "cache_read_tokens": 0,
                                    "cache_write_tokens": 0}, "cost_usd_equivalent": 0.0, "model_seconds": 0.0,
                          "steps": 0, "nudged": False, "invalid_submissions": 0}
                session = await self._run(turn["prompt"], session, config, system, max_steps, record)
                if not out.exists():
                    record["nudged"] = True
                    session = await self._run(NUDGE, session, config, system, 2, record)
                submitted = json.loads(out.read_text()) if out.exists() else None
                reply = "\n\n".join(record["replies"])
                calls = record["tool_calls"]
                turns_out.append({
                    "prompt": turn["prompt"], "submitted": submitted, "reply": reply,
                    "stopped": "submitted" if submitted else ("max_steps" if record["steps"] >= max_steps else "no_submission"),
                    "steps": record["steps"], "tool_calls": calls, "usage": record["usage"],
                    "cost_usd_equivalent": round(record["cost_usd_equivalent"], 4),
                    "model_seconds": round(record["model_seconds"], 1), "thinking": "\n\n".join(record["thinking"]),
                    "nudged": record["nudged"],
                    "invalid_submissions": record["invalid_submissions"],
                    "malformed_tool_calls": 0,
                    "infra_affected": any(c.get("rate_limited") for c in calls),
                    "grade": grade(turn, reply, [{"tool": c["tool"], "arguments": c["arguments"]} for c in calls], submitted),
                })
        return {"turns": turns_out}

    async def _run(self, prompt: str, session: str | None, config: Path, system: str, max_turns: int,
                   record: dict[str, Any]) -> str | None:
        # Claude Code names an MCP tool mcp__<server>__<tool>. Told only "submit_answer", Opus looked
        # for it on the GA4GH server (mcp__ga4gh__submit_answer, 79 failed calls in two runs).
        system = system.replace("call submit_answer", f"call {SUBMIT_TOOL}")
        argv = [shutil.which("claude") or "claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
                "--model", self.name, "--system-prompt", system, "--tools", "",
                "--mcp-config", str(config), "--strict-mcp-config", "--setting-sources", "",
                "--allowedTools", "mcp__ga4gh", "mcp__bench", "--max-turns", str(max_turns)]
        if self.effort:
            argv += ["--effort", self.effort]
        if session:
            argv += ["--resume", session]
        env = {k: v for k, v in os.environ.items() if not k.startswith(("GA4GH_", "ANTHROPIC_API_KEY", "CLAUDE_CODE_"))}
        started = time.monotonic()
        proc = await asyncio.create_subprocess_exec(*argv, cwd=str(WORKDIR), env=env, stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE, limit=64 * 1024 * 1024)
        pending: dict[str, dict[str, Any]] = {}
        submits: set[str] = set()
        result: dict[str, Any] = {}
        try:
            assert proc.stdout is not None
            async for raw in proc.stdout:
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                kind = event.get("type")
                if kind == "system" and event.get("session_id"):
                    session = event["session_id"]
                elif kind == "assistant":
                    record["steps"] += 1
                    for block in (event.get("message") or {}).get("content") or []:
                        if block.get("type") == "tool_use":
                            name = block.get("name", "")
                            call = {"tool": name.split("__", 2)[-1] if name.startswith("mcp__ga4gh__") else name,
                                    "arguments": block.get("input") or {}, "source": "claude-code"}
                            if name.startswith("mcp__bench__"):
                                submits.add(block.get("id", ""))
                            else:
                                pending[block.get("id", "")] = call
                                record["tool_calls"].append(call)
                        elif block.get("type") == "text" and block.get("text", "").strip():
                            record["replies"].append(block["text"])
                        elif block.get("type") == "thinking":
                            record["thinking"].append(block.get("thinking", ""))
                elif kind == "user":
                    for block in (event.get("message") or {}).get("content") or []:
                        if block.get("type") == "tool_result" and block.get("tool_use_id") in submits:
                            if block.get("is_error") or "validation error" in str(block.get("content")).lower():
                                record["invalid_submissions"] += 1
                        if block.get("type") == "tool_result" and block.get("tool_use_id") in pending:
                            text = block.get("content")
                            if isinstance(text, list):
                                text = "\n".join(c.get("text", "") for c in text if isinstance(c, dict))
                            text = str(text or "")
                            pending[block["tool_use_id"]].update(is_error=bool(block.get("is_error")),
                                                                 chars=len(text), head=text[:600])
                elif kind == "result":
                    result = event
            await proc.wait()
        except asyncio.CancelledError:
            proc.kill()
            raise
        record["model_seconds"] += time.monotonic() - started
        if result.get("is_error") and any(s.lower() in str(result.get("result", "")).lower() for s in _LIMIT):
            raise SubscriptionLimit(str(result.get("result"))[:300])
        if not result and proc.returncode:
            err = (await proc.stderr.read()).decode()[:300] if proc.stderr else ""
            raise RuntimeError(f"claude exited {proc.returncode}: {err}")
        usage = result.get("usage") or {}
        record["usage"]["prompt_tokens"] += usage.get("input_tokens", 0)
        record["usage"]["completion_tokens"] += usage.get("output_tokens", 0)
        record["usage"]["cache_read_tokens"] += usage.get("cache_read_input_tokens", 0)
        record["usage"]["cache_write_tokens"] += usage.get("cache_creation_input_tokens", 0)
        record["cost_usd_equivalent"] += result.get("total_cost_usd") or 0.0
        return result.get("session_id") or session


def _version() -> str | None:
    import subprocess
    try:
        return subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:  # noqa: BLE001
        return None
