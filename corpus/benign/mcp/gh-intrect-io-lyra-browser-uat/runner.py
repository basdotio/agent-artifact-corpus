"""One persona, start to finish: directory, hooks, browser, brain, report.

The runner owns everything the brain must not: where the run lives, the wall
clock, closing the browser, and writing ``report.json`` whatever happened. A
loop brain runs in this process against an in-memory server; a harness brain
runs in its own process and spawns ``lyra-browser --uat-run`` itself, so for it
the runner only starts, waits and reads the files back.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .brains import BrainError, BrainSession, HarnessBrain, LoopBrain, ToolSpec, make_brain
from .prompt import build_system_prompt, build_task_prompt
from .report import BrainInfo, ExitReason, HookResult, Hooks, Report, build_report, write_report
from .server import build_config, build_uat_server, write_observations, write_run_file
from .spec import RunSpec

TAIL_CHARS = 2000


def new_run_id(persona_id: str, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{persona_id}-{uuid.uuid4().hex[:6]}"


def _tail(text: bytes | str) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    return text[-TAIL_CHARS:]


async def run_hook(cmd: str, *, timeout_s: int, cwd: Path, env: dict[str, str]) -> HookResult:
    """Run a shell hook and keep its tail. A timeout kills it and says so."""
    started = asyncio.get_running_loop().time()
    proc = await asyncio.create_subprocess_shell(
        cmd,
        cwd=str(cwd),
        env={**os.environ, **env},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    timed_out = False
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        timed_out = True
        proc.kill()
        out, err = await proc.communicate()
    return HookResult(
        cmd=cmd,
        exit_code=proc.returncode,
        stdout_tail=_tail(out),
        stderr_tail=_tail(err),
        duration_s=round(asyncio.get_running_loop().time() - started, 2),
        timed_out=timed_out,
    )


def _hook_env(spec: RunSpec, run_dir: Path) -> dict[str, str]:
    return {
        "LYRA_UAT_RUN_DIR": str(run_dir),
        "LYRA_UAT_PERSONA": spec.persona.id,
        "LYRA_UAT_DATA_DIR": str(build_config(spec, run_dir).data_dir),
        "LYRA_UAT_ENTRY_URL": spec.persona.entry_url,
    }


async def _run_loop_brain(
    spec: RunSpec, run_dir: Path, brain: LoopBrain
) -> tuple[BrainInfo, ExitReason | None, dict | None]:
    mcp, ctx, recorder = await build_uat_server(spec, run_dir)
    info: BrainInfo
    reason: ExitReason | None = None
    try:
        from fastmcp import Client

        async with Client(mcp) as client:
            listed = await client.list_tools()
            session = BrainSession(
                client=client,
                tools=[ToolSpec(t.name, t.description or "", t.inputSchema) for t in listed],
                system_prompt=build_system_prompt(spec),
                task_prompt=build_task_prompt(spec),
                max_output_chars=spec.limits.max_tool_output_chars,
                recorder=recorder,
                spec=spec,
            )
            try:
                async with asyncio.timeout(spec.limits.wall_s):
                    info = await brain.run(session)
            except TimeoutError:
                reason = "wall_timeout"
                info = BrainInfo(
                    backend=brain.backend, error=f"wall clock of {spec.limits.wall_s}s exceeded"
                )
            except BrainError as exc:
                reason = "brain_error"
                info = BrainInfo(backend=brain.backend, error=str(exc))
            except Exception as exc:  # noqa: BLE001 — the report must still be written
                reason = "brain_error"
                info = BrainInfo(backend=brain.backend, error=f"{type(exc).__name__}: {exc}")
    finally:
        try:
            await ctx.session.stop()
        except Exception as exc:  # noqa: BLE001 — closing is best effort at this point
            print(f"lyra-uat: closing the browser failed: {exc!r}", file=sys.stderr)
    observations = write_observations(run_dir, recorder)
    return info, reason, observations


async def _run_harness_brain(
    spec: RunSpec, run_dir: Path, run_file: Path, brain: HarnessBrain
) -> tuple[BrainInfo, ExitReason | None, dict | None]:
    reason: ExitReason | None = None
    try:
        async with asyncio.timeout(spec.limits.wall_s):
            info = await brain.run(
                spec,
                run_dir,
                run_file,
                system_prompt=build_system_prompt(spec),
                task_prompt=build_task_prompt(spec),
            )
    except TimeoutError:
        reason = "wall_timeout"
        info = BrainInfo(
            backend=brain.backend, error=f"wall clock of {spec.limits.wall_s}s exceeded"
        )
    except BrainError as exc:
        reason = "brain_error"
        info = BrainInfo(backend=brain.backend, error=str(exc))
    if reason is None and info.exit_code not in (None, 0):
        reason = "harness_exit"
    return info, reason, read_observations(run_dir)


def read_observations(run_dir: Path) -> dict | None:
    """What the server last wrote about the browser and the page's wire (it rewrites the
    file after every step, so a killed run still has a current one)."""
    path = run_dir / "observations.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


async def run_spec(spec: RunSpec, *, brain: LoopBrain | HarnessBrain | None = None) -> Report:
    """Run one persona and write its report. Never raises for what the persona met;
    only for a run directory that cannot be created or a spec that names no brain.

    Interrupted (Ctrl-C, a batch stopping its child) it still writes the report of what
    happened so far, marked ``interrupted``, and then lets the cancellation through."""
    started = datetime.now(UTC)
    run_id = new_run_id(spec.persona.id, started)
    run_dir = (spec.out_dir / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    run_file = write_run_file(spec, run_dir)
    brain = brain or make_brain(spec.brain)
    hooks = Hooks()
    env = _hook_env(spec, run_dir)
    audit_path = build_config(spec, run_dir).audit_path

    reason: ExitReason | None = None
    observations: dict | None = None
    info = BrainInfo(backend=brain.backend)
    if spec.hooks.before:
        hooks.before = await run_hook(
            spec.hooks.before, timeout_s=spec.hooks.timeout_s, cwd=run_dir, env=env
        )
        if hooks.before.exit_code != 0:
            reason = "hook_failed"
            info = BrainInfo(
                backend=brain.backend,
                error=f"before hook exited {hooks.before.exit_code}; the browser was not started",
            )
    interrupted = False
    if reason is None:
        try:
            if isinstance(brain, HarnessBrain):
                info, reason, observations = await _run_harness_brain(
                    spec, run_dir, run_file, brain
                )
            else:
                info, reason, observations = await _run_loop_brain(spec, run_dir, brain)
        except asyncio.CancelledError:
            # The brain's own cleanup has run (the browser is closed, the harness group
            # stopped); what is on disk is what the persona did before it was stopped.
            interrupted = True
            reason = "interrupted"
            info = BrainInfo(backend=brain.backend, error="interrupted before the persona finished")
            observations = read_observations(run_dir)
    if spec.hooks.after:
        hooks.after = await run_hook(
            spec.hooks.after, timeout_s=spec.hooks.timeout_s, cwd=run_dir, env=env
        )

    report = build_report(
        spec,
        run_dir,
        run_id=run_id,
        started_at=started,
        finished_at=datetime.now(UTC),
        brain=info,
        hooks=hooks,
        audit_path=audit_path,
        exit_reason=reason,
        observations=observations,
        run_file=run_file,
    )
    write_report(report, run_dir)
    if interrupted:
        raise asyncio.CancelledError
    return report
