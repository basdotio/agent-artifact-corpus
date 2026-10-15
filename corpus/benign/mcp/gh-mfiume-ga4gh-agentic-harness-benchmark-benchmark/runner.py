"""Run tasks: drive a model through the GA4GH MCP server, record every turn, grade it.

    python -m benchmark.runner --model ollama:gpt-oss:20b --effort low --out runs/gpt-oss-low \\
        [--split dev] [--mcp-src WORKTREE] [--sdk-src WORKTREE] [--tasks PATTERN] [--limit N]

The MCP server is started once per run over stdio, configured with the public GA4GH
Implementation Registry only and no write scopes, and with every inherited GA4GH_* setting
removed. Each task starts a fresh conversation; each turn loops model -> tools -> model until
the model calls submit_answer (see answer.py) or reaches --max-steps. The server's upstream HTTP
goes through the HTTP cassette (see http_cassette.py), so MCP builds under test see the same
frozen services. A task that fails inside the framework is recorded with its error
and the run continues; rerunning with the same --out resumes, skipping finished tasks.
"""

from __future__ import annotations

import argparse
import asyncio
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
import traceback
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from . import answer
from .cassette import MODES, Cassette
from .infra import row_hit, turn_hit
from .checks import grade_turn
from .models import MalformedToolCall, make_model
from .tasks import ROOT, load

_RATE_LIMITED = re.compile(r"rate limit exceeded|too many requests|throttled|HTTP 429|\"status_code\": ?429", re.IGNORECASE)
# Failures to reach something. Recorded only if the network is up at the time: with the network
# down every service looks dead, and a recorded outage would be replayed to every later model.
_UNREACHABLE = re.compile(
    r"unavailable|unreachable|ConnectError|ConnectTimeout|ReadTimeout|timed out|nodename nor servname|"
    r"Name or service not known|Temporary failure in name resolution|Network is unreachable|"
    r"\"type\": ?\"(upstream|transport|timeout)\"", re.IGNORECASE)
NETWORK_CHECK_URL = "https://implementation-registry.ga4gh.org/api/services"
PUBLIC_REGISTRY = "implementation-registry=https://implementation-registry.ga4gh.org/api"
DEV = Path.home() / "Development"
SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text()


def _attr(obj: Any, *names: str) -> Any:
    """MCP SDK 2.x uses snake_case field names where 1.x used camelCase."""
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


class Network:
    """Is this machine online? Checked against the registry, cached for 20 s."""

    def __init__(self) -> None:
        self._checked, self._ok = 0.0, True

    async def ok(self) -> bool:
        if time.monotonic() - self._checked < 20:
            return self._ok
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                self._ok = (await client.get(NETWORK_CHECK_URL)).status_code < 500
        except Exception:  # noqa: BLE001
            self._ok = False
        self._checked = time.monotonic()
        return self._ok

    async def wait(self, limit: float = 3600) -> bool:
        """Block until online (checking every 30 s), up to limit seconds."""
        started = time.monotonic()
        while not await self.ok():
            if time.monotonic() - started > limit:
                return False
            print("network down; waiting", flush=True)
            await asyncio.sleep(30)
            self._checked = 0.0
        return True


class ToolBox:
    """The MCP server's tools, with results passed through the cassette and truncated alike for all models."""

    def __init__(self, session: ClientSession, cassette: Cassette, max_chars: int, tool_timeout: float) -> None:
        self.session, self.cassette = session, cassette
        self.max_chars, self.tool_timeout = max_chars, tool_timeout
        self.schemas: list[dict[str, Any]] = []
        self.names: set[str] = set()
        self.instructions = ""
        self.network = Network()

    async def load(self) -> None:
        result = await self.session.list_tools()
        self.schemas = [{"type": "function", "function": {
            "name": t.name, "description": (t.description or "")[:1024],
            "parameters": _attr(t, "input_schema", "inputSchema") or {"type": "object", "properties": {}}}}
            for t in result.tools]
        self.names = {t.name for t in result.tools}

    async def call(self, name: str, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """The text the model sees, and a record of the call."""
        record: dict[str, Any] = {"tool": name, "arguments": arguments}
        if name not in self.names:
            record.update(source="refused", error="unknown tool")
            return f"Error: there is no tool named {name!r}.", record
        cached = self.cassette.get(name, arguments)
        if cached is not None:
            result = cached["result"]
            record["source"] = "cassette"
        elif self.cassette.mode == "replay":
            record.update(source="refused", error="not recorded")
            return "Error: this call was not recorded, so it cannot be replayed.", record
        else:
            started = time.monotonic()
            try:
                response = await asyncio.wait_for(self.session.call_tool(name, arguments), self.tool_timeout)
                text = "\n".join(getattr(c, "text", "") for c in response.content if getattr(c, "type", "") == "text")
                result = {"text": text, "is_error": bool(_attr(response, "is_error", "isError"))}
            except asyncio.TimeoutError:
                result = {"text": f"Error: the tool did not answer within {self.tool_timeout:g} s.", "is_error": True}
            except Exception as exc:  # noqa: BLE001  a tool failure is the model's to handle
                result = {"text": f"Error: {exc.__class__.__name__}: {exc}", "is_error": True}
            record["seconds"] = round(time.monotonic() - started, 2)
            record["source"] = "live"
            # Timeouts and rate limits are not stored: a later run may get a real answer, and a
            # recorded throttle would be replayed to every later model.
            if _RATE_LIMITED.search(result["text"]):
                record["rate_limited"] = True
            elif _UNREACHABLE.search(result["text"][:2000]) and not await self.network.ok():
                record["network_down"] = True
            elif "did not answer within" not in result["text"]:
                self.cassette.put(name, arguments, result)
        text = result["text"]
        # The head of the result, so failures can be attributed later without the full text.
        record.update(is_error=result.get("is_error", False), chars=len(text), head=text[:600])
        if len(text) > self.max_chars:
            text = text[: self.max_chars] + f"\n[... truncated: {len(text) - self.max_chars} more characters]"
            record["truncated"] = True
        return text, record


NUDGE = "Call submit_answer with your final answer."


async def run_task(task: dict[str, Any], model: Any, tools: ToolBox, max_steps: int) -> dict[str, Any]:
    system = SYSTEM + ("\n\nThe tool server describes itself as follows:\n" + tools.instructions if tools.instructions else "")
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    turns_out = []
    for turn in task["turns"]:
        messages.append({"role": "user", "content": turn["prompt"]})
        submit = answer.tool(turn)
        schemas = tools.schemas + [submit]
        calls: list[dict[str, Any]] = []
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        model_seconds, steps, stopped = 0.0, 0, "submitted"
        thinking: list[str] = []
        replies: list[str] = []
        submitted: dict[str, Any] | None = None
        invalid_submissions, nudged, malformed = 0, False, 0
        while submitted is None:
            out_of_steps = steps >= max_steps
            if out_of_steps:
                # One last chance to answer from what it has: only submit_answer is offered.
                messages.append({"role": "user", "content": "Tool budget reached. " + NUDGE})
            try:
                reply = await model.chat(messages, [submit] if out_of_steps else schemas)
            except MalformedToolCall:
                # Told plainly, as an API would, and capped: the model's error, scored as such.
                malformed += 1
                if malformed > 2:
                    stopped = "malformed_tool_calls"
                    break
                messages.append({"role": "user", "content": "Your last tool call could not be parsed. Call a tool with valid JSON arguments."})
                continue
            model_seconds += reply.seconds
            if reply.thinking:
                thinking.append(reply.thinking)
            if reply.content.strip():
                replies.append(reply.content)
            for k in usage:
                usage[k] += reply.usage.get(k, 0)
            if not reply.tool_calls:
                messages.append({"role": "assistant", "content": reply.content})
                if out_of_steps or nudged:
                    stopped = "max_steps" if out_of_steps else "no_submission"
                    break
                # The turn ends only with submit_answer. One neutral reminder, the same for
                # every model, and recorded.
                nudged = True
                messages.append({"role": "user", "content": NUDGE})
                continue
            messages.append({"role": "assistant", "content": reply.content, "tool_calls": reply.tool_calls})
            for call in reply.tool_calls:
                if call["name"] == answer.NAME:
                    error = answer.validate(turn, call["arguments"])
                    if error:
                        invalid_submissions += 1
                        messages.append({"role": "tool", "name": answer.NAME, "content": error})
                        continue
                    submitted = call["arguments"]
                    messages.append({"role": "tool", "name": answer.NAME, "content": "Answer recorded."})
                    break
                if out_of_steps:
                    messages.append({"role": "tool", "name": call["name"], "content": "Error: the tool budget is spent."})
                    continue
                text, record = await tools.call(call["name"], call["arguments"])
                calls.append(record)
                messages.append({"role": "tool", "name": call["name"], "content": text})
            if out_of_steps:
                if submitted is None:
                    stopped = "max_steps"
                break
            steps += 1
        if submitted is not None and steps >= max_steps:
            stopped = "submitted_at_budget"
        grade_calls = [{"tool": c["tool"], "arguments": c["arguments"]} for c in calls]
        infra = [c["tool"] for c in calls if c.get("rate_limited") or c.get("network_down")]
        reply_text = "\n\n".join(replies)
        turns_out.append({
            "prompt": turn["prompt"], "submitted": submitted, "reply": reply_text, "stopped": stopped,
            "steps": steps, "tool_calls": calls, "usage": usage, "model_seconds": round(model_seconds, 1),
            "thinking": "\n\n".join(thinking),
            "nudged": nudged,
            "invalid_submissions": invalid_submissions,
            "malformed_tool_calls": malformed,
            # A rate-limited service answer is an infrastructure failure, not the model's.
            "infra_affected": bool(infra),
            "grade": grade_turn(turn, reply_text, grade_calls, submitted),
        })
    return {"turns": turns_out}


def _commit(path: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def _dirty(path: Path) -> bool | None:
    try:
        return bool(subprocess.run(["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"],
                                   capture_output=True, text=True, check=True).stdout.strip())
    except Exception:  # noqa: BLE001
        return None


def _server(args: argparse.Namespace, out: Path) -> dict[str, Any]:
    """How to start the MCP server: its Python, with the MCP and SDK source trees under test first on
    the path (so an experiment's worktrees replace the installed ones), and the HTTP cassette installed."""
    python = Path(os.path.expanduser(args.mcp_python))
    mcp_src, sdk_src = Path(os.path.expanduser(args.mcp_src)), Path(os.path.expanduser(args.sdk_src))
    env = {k: v for k, v in os.environ.items() if not k.startswith("GA4GH_")}
    env["GA4GH_MCP_READ_TIMEOUT"] = "45"
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(mcp_src / "src"), str(sdk_src / "src")])
    env["BENCH_HTTP_CASSETTE"] = str(Path(args.http_cassette).resolve())
    env["BENCH_HTTP_MODE"] = args.http_mode
    return {
        "command": str(python), "args": ["-m", "benchmark.mcp_launch", "--registry", PUBLIC_REGISTRY], "env": env,
        "manifest": {"mcp_python": str(python), "mcp_src": str(mcp_src), "sdk_src": str(sdk_src),
                     "mcp_commit": _commit(mcp_src), "mcp_dirty": _dirty(mcp_src),
                     "sdk_commit": _commit(sdk_src), "sdk_dirty": _dirty(sdk_src)},
    }


async def main_async(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tasks, facts = load()
    if args.task_file:
        wanted = set(Path(args.task_file).read_text().split())
        tasks = [t for t in tasks if t["id"] in wanted]
    if args.tasks:
        patterns = args.tasks.split(",")
        tasks = [t for t in tasks if any(fnmatch.fnmatch(t["id"], p) for p in patterns)]
    if args.split != "all":
        split = json.loads((ROOT / "splits" / "v1.json").read_text())
        tasks = [t for t in tasks if split["tasks"].get(t["id"]) == args.split]
    if args.order == "shuffle":
        import random
        random.Random(0).shuffle(tasks)
    if args.limit:
        tasks = tasks[: args.limit]
    results_path = out / "results.jsonl"
    by_id = {t["id"]: t for t in tasks}
    done = set()
    if results_path.is_file():
        for line in results_path.read_text().splitlines():
            row = json.loads(line)
            if row.get("interrupted_by_sleep") or row_hit(row):
                continue  # always rerun
            task = by_id.get(row["task_id"])
            if task and any(i < len(task["turns"]) and t.get("prompt") != task["turns"][i]["prompt"]
                            for i, t in enumerate(row.get("turns") or [])):
                continue  # the task was revised after this run: run it again
            if row.get("status") == "ok" or not args.retry_errors:
                done.add((row["task_id"], row["repeat"]))
    temperature = args.temperature if args.temperature >= 0 else None
    model = make_model(args.model, effort=args.effort, num_ctx=args.num_ctx, temperature=temperature, seed=args.seed)
    cassette = Cassette(Path(args.tool_cassette), args.mode) if args.tool_cassette else Cassette(out / "no-tool-cassette.jsonl", "live")
    server = _server(args, out)
    manifest = {
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "model": model.describe(),
        **server["manifest"],
        "benchmark_commit": _commit(ROOT), "snapshot": facts["fetched_at"],
        "http_cassette": args.http_cassette, "http_mode": args.http_mode, "tool_cassette": args.tool_cassette,
        "split": args.split, "tool_filter": args.tool_filter,
        "tasks": len(tasks), "repeats": args.repeats, "first_seed": args.seed, "task_file": args.task_file, "max_steps": args.max_steps,
        "max_result_chars": args.max_result_chars, "registry": PUBLIC_REGISTRY,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    with (out / "manifests.jsonl").open("a") as handle:  # every invocation, since seed ranges differ
        handle.write(json.dumps(manifest) + "\n")
    params = StdioServerParameters(command=server["command"], args=server["args"], env=server["env"], cwd=str(out))
    async with AsyncExitStack() as stack:
        errlog = stack.enter_context((out / "mcp-server.log").open("a"))
        read, write = await stack.enter_async_context(stdio_client(params, errlog=errlog))
        session = await stack.enter_async_context(ClientSession(read, write))
        init = await session.initialize()
        tools = ToolBox(session, cassette, args.max_result_chars, args.tool_timeout)
        if hasattr(model, "run_task"):
            # Claude Code starts its own copy of the same server, through the same cassette.
            # submit_server uses the MCP server's environment (MCP SDK 1.x).
            model.server = {**server, "bench_python": server["command"], "bench_env": {"PYTHONPATH": str(ROOT)}}
        tools.instructions = getattr(init, "instructions", "") or ""
        await tools.load()
        if args.tool_filter:
            keep = args.tool_filter.split(",")
            tools.schemas = [t for t in tools.schemas if any(fnmatch.fnmatch(t["function"]["name"], p) for p in keep)]
            tools.names = {t["function"]["name"] for t in tools.schemas}
        print(f"{len(tools.schemas)} tools; {len(tasks)} tasks x {args.repeats}; cassette {len(cassette)} entries; "
              f"{len(done)} already done", flush=True)
        consecutive_errors = 0
        for offset in range(args.repeats):
            # Repeats differ by seed only, and a row's "repeat" is its seed, so runs that cover
            # different seed ranges pair up by (task, seed).
            repeat = model.seed = args.seed + offset
            for index, task in enumerate(tasks, 1):
                if (task["id"], repeat) in done:
                    continue
                if not await tools.network.wait():
                    print("stopping: offline for an hour", flush=True)
                    return
                started, wall_started = time.monotonic(), time.time()
                row: dict[str, Any] = {"task_id": task["id"], "repeat": repeat, "category": task["category"],
                                       "difficulty": task["difficulty"]}
                try:
                    if hasattr(model, "run_task"):
                        job = model.run_task(task, SYSTEM, args.max_steps, grade_turn)
                    else:
                        job = run_task(task, model, tools, args.max_steps)
                    result = await asyncio.wait_for(job, args.task_timeout)
                    row.update(status="ok", **result)
                    if any(t.get("infra_affected") or turn_hit(t) for t in result["turns"]):
                        row["infra_affected"] = True  # rerun on resume
                except asyncio.TimeoutError:
                    row.update(status="error", error=f"task exceeded {args.task_timeout:g} s")
                except Exception as exc:  # noqa: BLE001  record and continue
                    row.update(status="error", error=f"{exc.__class__.__name__}: {exc}",
                               traceback=traceback.format_exc(limit=6))
                row["seconds"] = round(time.monotonic() - started, 1)
                row["wall_seconds"] = round(time.time() - wall_started, 1)
                # macOS's monotonic clock stops while the machine sleeps; a gap means the task ran
                # across a sleep, when requests in flight fail. Such a task is not scored and reruns.
                if row["wall_seconds"] - row["seconds"] > 20:
                    row["interrupted_by_sleep"] = True
                with results_path.open("a") as handle:
                    handle.write(json.dumps(row) + "\n")
                consecutive_errors = consecutive_errors + 1 if row["status"] != "ok" else 0
                if consecutive_errors >= 5:
                    print("stopping: 5 framework errors in a row; fix and rerun with --retry-errors", flush=True)
                    return
                verdicts = [t["grade"].get("answer", {}).get("verdict", "-") for t in row.get("turns", [])]
                print(f"[{repeat}:{index}/{len(tasks)}] {task['id']} {row['status']} {row['seconds']}s {verdicts}"
                      + (f" {row.get('error', '')[:120]}" if row["status"] != "ok" else ""), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", required=True, help="ollama:<name>")
    parser.add_argument("--effort", choices=["low", "medium", "high"])
    parser.add_argument("--mcp-python", default=str(DEV / "ga4gh-mcp-service-agentic-integration/.venv/bin/python"),
                        help="the Python environment the MCP server is installed in")
    parser.add_argument("--mcp-src", default=str(DEV / "ga4gh-mcp-service-agentic-integration"),
                        help="MCP server source tree under test (a worktree, for an experiment)")
    parser.add_argument("--sdk-src", default=str(DEV / "ga4gh-agentic-harness-python-integration"),
                        help="Harness SDK source tree under test")
    parser.add_argument("--out", required=True)
    parser.add_argument("--http-cassette", default=str(ROOT / "cassettes" / "http.jsonl"),
                        help="recorded upstream HTTP, replayed below the MCP server")
    parser.add_argument("--http-mode", choices=MODES, default="replay-or-record")
    parser.add_argument("--tool-cassette", help="legacy: recorded tool results, in front of the server (off by default)")
    parser.add_argument("--mode", choices=MODES, default="replay-or-record", help="tool cassette mode")
    parser.add_argument("--split", choices=["all", "dev", "heldout"], default="all", help="splits/v1.json")
    parser.add_argument("--tool-filter", help="expose only tools matching these comma-separated globs, e.g. 'ga4gh_*'")
    parser.add_argument("--tasks", help="comma-separated id patterns, e.g. 'beacon.*,drs.size.*'")
    parser.add_argument("--task-file", help="only the task ids listed in this file, one per line")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--max-result-chars", type=int, default=40000)
    parser.add_argument("--num-ctx", type=int, default=65536)
    parser.add_argument("--order", choices=["file", "shuffle"], default="shuffle",
                        help="shuffle (fixed seed) spreads rate-limited services' calls across the run")
    parser.add_argument("--temperature", type=float, default=1.0,
                        help="pinned; 1.0 is gpt-oss's own default. A negative value leaves the model's own default")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--tool-timeout", type=float, default=90)
    parser.add_argument("--task-timeout", type=float, default=1200)
    parser.add_argument("--retry-errors", action="store_true", help="rerun tasks that ended in a framework error")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
