"""Launch agent sessions, and run a whole analysis with a fixed policy in place of the researcher.

One session = one harness process with one task prompt (the method's stages/<task>.md), attached
to the run's MCP server and nothing else: no file, shell or web tools unless asked for, no user
settings, no memory, no CLAUDE.md. Everything about the session (prompt, its hash, harness and
version, model, flags, the full transcript) is recorded for the researcher in the ledger and
logs/<run>/<session>.jsonl. The agent sees none of it.

    qls agent RUN --task calibrate --sources P01 P02 P03     one session
    qls pipeline RUN --auto                                   all stages, AI-only

The AI-only policy stands in for the researcher at every checkpoint: it approves every codebook
proposal as written, answers nothing, and moves the run to the next stage when a stage's task is
done. It acts as auto:NAME, so its decisions are never mistaken for a person's.
"""

from __future__ import annotations

import glob
import json
import os
import random
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from .project import Project
from .session import Session
from .util import QlsError, now

HARNESS = "claude-code"


def claude_binary(project: Project) -> str:
    cand = os.environ.get("QLS_CLAUDE") or project.cfg("agent", "command") or shutil.which("claude")
    if not cand:
        found = sorted(glob.glob(os.path.expanduser("~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude")))
        cand = found[-1] if found else None
    if not cand or not Path(cand).exists():
        raise QlsError("Claude Code not found: set QLS_CLAUDE, or [agent] command in qls.toml.")
    return cand


def render(template: str, sources: list[str]) -> str:
    return template.replace("{sources}", ", ".join(sources)).replace("{source}", sources[0] if sources else "")


def run_session(p: Project, run: str, task: str, sources: list[str] | None = None, actor: str = "agent:scholar-1",
                model: str = "opus", web: bool = False, timeout: int = 4 * 3600) -> dict:
    """Run one agent session to completion. Returns the session record."""
    s = Session(p, run, "reviewer:launcher")
    if task not in s.m.tasks:
        raise QlsError(f"No task {task!r} in method {s.m.name}. Tasks: {', '.join(sorted(s.m.tasks))}")
    sources = list(sources or [])
    prompt = render(s.m.tasks[task], sources)
    sid = f"{run}-{task}-{uuid.uuid4().hex[:8]}"
    work = p.root / "agents" / run / sid          # an empty folder: the agent's whole world is the MCP server
    work.mkdir(parents=True, exist_ok=True)
    log = p.root / "logs" / run / f"{sid}.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)

    env_srv = {"QLS_SESSION": sid, "QLS_HARNESS": HARNESS, "QLS_TASK": task, "QLS_MODEL": model,
               **{k: os.environ[k] for k in ("QLS_TYPEDB", "QLS_TYPEDB_USER", "QLS_TYPEDB_PASSWORD") if k in os.environ}}
    mcp = {"mcpServers": {"qls": {"command": sys.executable,
                                  "args": ["-m", "qls", "mcp", "--project", str(p.root), "--run", run, "--actor", actor],
                                  "env": env_srv}}}
    (work / ".mcp.json").write_text(json.dumps(mcp, indent=1))

    tools = "WebSearch,WebFetch" if web else ""
    claude = claude_binary(p)
    cmd = [claude, "-p", "--model", model, "--tools", tools, "--strict-mcp-config", "--mcp-config", str(work / ".mcp.json"),
           "--allowedTools", "mcp__qls" + (",WebSearch,WebFetch" if web else ""), "--permission-mode", "dontAsk",
           "--setting-sources", "", "--output-format", "stream-json", "--verbose", "--no-session-persistence"]
    version = subprocess.run([claude, "--version"], capture_output=True, text=True).stdout.strip()
    config = {"cmd": cmd[1:], "harness_version": version, "web": web, "sources": sources, "cwd": str(work),
              "method_hash": s.run["method_hash"]}
    p.ledger.start_session(sid, run, actor, task, s.stage(), prompt, HARNESS, model, config, str(log.relative_to(p.root)))

    # a clean environment: nothing from the researcher's own Claude Code session or editor leaks in
    env = {k: v for k, v in os.environ.items() if not k.startswith(("QLS_", "CLAUDE_CODE", "CLAUDECODE", "VSCODE"))}
    actual_model, result = None, {}
    with open(log, "w", encoding="utf-8") as f:
        proc = subprocess.Popen(cmd, cwd=work, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        proc.stdin.write(prompt)
        proc.stdin.close()
        try:
            for line in proc.stdout:
                f.write(line)
                f.flush()
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if msg.get("type") == "system" and msg.get("subtype") == "init":
                    actual_model = msg.get("model")
                    tools_seen = msg.get("tools", [])
                    if any(not t.startswith("mcp__qls") and t not in ("WebSearch", "WebFetch") for t in tools_seen):
                        f.write(json.dumps({"qls_warning": "agent had tools beyond the qls server", "tools": tools_seen}) + "\n")
                elif msg.get("type") == "result":
                    result = {k: msg.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms", "total_cost_usd", "result")}
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            code = -9
    p.ledger.end_session(sid, code, actual_model)
    return {"session": sid, "task": task, "sources": sources, "exit": code, "model": actual_model, "log": str(log), **result}


# ------------------------------------------------------------------ AI-only policy

def policy_step(p: Project, run: str, actor: str, advance: bool) -> list[str]:
    """What the auto researcher does at a checkpoint: approve all proposals, resume, maybe move on."""
    s = Session(p, run, actor)
    done = []
    proposed = s.G.column(s.db, 'match $e isa codebook-entry, has status "proposed", has id $i; select $i;', "i")
    for cid in sorted(proposed, key=lambda x: int(x.split("-")[-1])):
        r = s.approve(cid, note="auto policy: approved as proposed")
        done.append(f"approve {cid}: {'ok' if r.get('ok') else r.get('error')}")
    if s.run["status"] == "waiting":
        s.resume("auto policy: no feedback")
        done.append("resume")
    if advance:
        r = s.set_stage("next", "auto policy: stage task done")
        done.append(f"stage -> {r.get('stage') if r.get('ok') else r.get('error')}")
    return done


def coded_sources(s: Session) -> list[str]:
    """Sources an agent has worked through: begun, or given an interview memo (agents sometimes read with
    read_source and never call begin)."""
    begun = {e["params"]["source"] for e in s.L.events(s.run_id) if e["action"] == "begin" and not e["actor"].startswith(("human", "auto"))}
    memoed = set(s.G.column(s.db, 'match $m isa memo, has memo-level "interview"; about (memo: $m, target: $s); '
                                  '$s isa source, has id $i; select $i;', "i"))
    return sorted(begun | memoed)


# How `qls pipeline` schedules sessions in each stage. A method can say so in its stages.yaml
# (run: once | per_source | calibration; task; sources: uncoded | all; after). The Gioia method's
# stages.yaml predates these fields and is kept unchanged (editing a method changes its hash and
# would block forking existing runs), so its schedule is given here.
GIOIA_SCHEDULE = {
    "calibrate": {"run": "calibration", "task": "calibrate"},
    "first_order": {"run": "per_source", "sources": "uncoded", "task": "first_order", "after": "first_order_batch"},
}


def schedule(stage: dict) -> dict:
    base = GIOIA_SCHEDULE.get(stage["id"], {"run": "once", "task": stage["id"]})
    return {**base, **{k: stage[k] for k in ("run", "task", "sources", "after") if k in stage}}


def pipeline(p: Project, run: str, calibration: int | None = None, seed: int = 1, batch: int = 0,
             actor: str = "agent:scholar-1", policy: str = "auto:approve-all", model: str = "opus",
             until: str | None = None, say=print) -> None:
    """Run the method's stages from wherever the run is, with the AI-only policy at every checkpoint.
    calibration: k interviews for a calibration stage (required if the method has one).
    batch: n interviews per batch in per-interview stages (0 = no batches: one review after all)."""
    s = Session(p, run, "reviewer:launcher")
    stages = s.m.stages
    if not stages:
        raise QlsError(f"Method {s.m.name} declares no stages; run sessions with `qls agent`.")
    if any(schedule(x)["run"] == "calibration" for x in stages) and not calibration:
        raise QlsError("This method has a calibration stage: give --calibration K (interviews to calibrate on).")
    order = sorted(s.run["config"]["sources"])
    random.Random(seed).shuffle(order)
    say(f"[{now()}] {run}: method {s.m.name}, stage {s.stage()}, source order (seed {seed}): {' '.join(order)}")

    def session(task, srcs=None):
        say(f"[{now()}] session {task} {' '.join(srcs or [])}")
        r = run_session(p, run, task, srcs, actor, model)
        say(f"[{now()}]   exit {r['exit']}, {r.get('num_turns')} turns, {round((r.get('duration_ms') or 0) / 60000)} min, "
            f"model {r.get('model')}, cost {r.get('total_cost_usd')}")
        if r["exit"] != 0 or r.get("is_error"):
            raise QlsError(f"session {r['session']} failed; see {r['log']}")
        return r

    def stop(advance):
        say("   policy: " + "; ".join(policy_step(p, run, policy, advance=advance)))

    ids = [x["id"] for x in stages]
    while True:
        cur = Session(p, run, "reviewer:launcher").stage()
        if cur == until:
            say(f"[{now()}] reached {until}; stopping")
            return
        sc = schedule(stages[ids.index(cur)])
        last = cur == ids[-1]
        if sc["run"] == "calibration":
            session(sc["task"], order[:calibration])
        elif sc["run"] == "per_source":
            done = coded_sources(Session(p, run, "reviewer:launcher")) if sc.get("sources", "uncoded") == "uncoded" else []
            todo = [x for x in order if x not in done]
            size = batch if batch > 0 else max(1, len(todo))
            for i in range(0, len(todo), size):
                chunk = todo[i:i + size]
                for src in chunk:
                    session(sc["task"], [src])
                    if Session(p, run, "reviewer:launcher").run["status"] == "waiting":
                        stop(False)
                if sc.get("after"):
                    session(sc["after"], chunk)
                    if i + size < len(todo):
                        stop(False)
        else:
            session(sc["task"])
        stop(not last)
        if last:
            say(f"[{now()}] {run}: done")
            return
