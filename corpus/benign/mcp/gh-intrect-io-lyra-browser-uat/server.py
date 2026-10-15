"""Assembling a lyra-browser server for one persona run.

The same server as ``build_server`` — same tools, permissions, guard and audit
log — with three differences: the configuration comes from the run spec (a
headless window of the persona's size, a profile of its own, the target's
sites trusted and nothing else, consent pinned to ``elicit`` so nobody can
answer for the user), the tools the persona is not offered are switched off,
and ``UatMiddleware`` records and guards every call.

``serve_stdio`` is what ``lyra-browser --uat-run <run.json>`` runs: an external
harness (Claude Code, Codex) spawns it as its MCP server and the run's files
appear in the run directory exactly as they would from our own loop.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from ..approval import CollaborationState
from ..audit import AuditLog
from ..config import Config
from ..context import ServerContext
from ..server import instructions_for
from ..session import BrowserSession
from ..tools import register_all
from ..tools import uat as uat_tools
from ..vision import VisionMiddleware
from .observe import PageObservers
from .recorder import RunRecorder, UatMiddleware
from .spec import UAT_TOOLS, RunSpec

RUN_FILE = "run.json"

_UAT_INSTRUCTIONS = """
UAT mode:
- You are playing one persona against a site under test; your task describes it.
- Every tool call is recorded by the server. Action steps (navigate, click, type,
  scroll ...) count against the persona's budget; reads do not. budget_exhausted
  means the budget is spent: report what remains with report_finding and call
  finish.
- report_finding, verdict, note and finish write the run's report. finish ends
  the run; after it every browser tool answers "finished".
- blocked_by_uat_policy means the server refused something the persona must never
  do (a card number, a file outside its upload directory). Do not try another way.
- screenshot and read_image attach the picture to their result when the client
  shows images; the image_path is also on disk for the trace.
"""


def build_config(spec: RunSpec, run_dir: Path) -> Config:
    """The browser configuration a persona runs with.

    Not ``Config.from_env``: a run must not inherit the operator's profile,
    their trusted sites or a consent channel that lets the model answer for them.
    """
    data_dir = (spec.data_dir or run_dir / "browser").expanduser()
    cfg = Config(
        client="generic",
        data_dir=data_dir,
        headless=spec.headless,
        viewport_width=spec.persona.viewport.width,
        viewport_height=spec.persona.viewport.height,
        proxy=spec.target.proxy,
        require_approval=True,
        # ``elicit``, never ``auto``: our own in-memory client declares no elicitation
        # capability, and with ``auto`` that would fall back to honouring the
        # model's own confirm=true.
        consent_channel="autonomous" if spec.target.policy == "autonomous" else "elicit",
        denied_origins=tuple(spec.target.deny_origins),
        # Unattended: nobody answers, so a prompt is a refusal — fail fast.
        consent_timeout_s=1.0,
        trusted_origins=tuple(spec.all_trusted_origins()),
        trusted_send_origins=tuple(spec.target.trusted_send_origins),
        guard_backend=spec.guard_backend,
        driver=spec.driver,
        # Every capture is evidence; nothing is pruned during a run.
        capture_keep=0,
    )
    cfg.capture_dir = run_dir / "captures"
    return cfg


def _run_file_payload(spec: RunSpec, run_dir: Path) -> dict[str, Any]:
    return {"spec": spec.model_dump(mode="json"), "run_dir": str(run_dir)}


def write_run_file(spec: RunSpec, run_dir: Path) -> Path:
    """What ``--uat-run`` reads: the spec and where the run lives."""
    path = run_dir / RUN_FILE
    path.write_text(
        json.dumps(_run_file_payload(spec, run_dir), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def read_run_file(path: Path) -> tuple[RunSpec, Path]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RunSpec.model_validate(payload["spec"]), Path(payload["run_dir"])


def make_recorder(spec: RunSpec, run_dir: Path) -> RunRecorder:
    return RunRecorder(
        run_dir,
        step_budget=spec.persona.step_budget,
        entry_url=spec.persona.entry_url,
        uploads_allowed_dir=spec.persona.uploads_allowed_dir,
        auto_screenshot=spec.limits.auto_screenshot,
        prior_finding_ids=[f.id for f in spec.prior_findings],
    )


async def build_uat_server(
    spec: RunSpec,
    run_dir: Path,
    *,
    recorder: RunRecorder | None = None,
    session_factory: Callable[[Config], Any] = BrowserSession,
) -> tuple[FastMCP, ServerContext, RunRecorder]:
    """The server, its context and the recorder for one run.

    ``session_factory`` exists for tests, which hand in a fake session; the
    default is the real browser.
    """
    cfg = build_config(spec, run_dir)
    recorder = recorder or make_recorder(spec, run_dir)
    ctx = ServerContext(
        config=cfg,
        session=session_factory(cfg),
        audit=AuditLog(cfg.audit_path),
        collab=CollaborationState(require_approval=True),
    )
    # Requests, console and page errors of every tab, for the report. The real
    # session calls each observer per adopted tab; a test double has no such list.
    observers = PageObservers(run_dir, capture_patterns=spec.target.network_capture)
    page_observers = getattr(ctx.session, "page_observers", None)
    if isinstance(page_observers, list):
        page_observers.append(observers.attach)
    recorder.observers = observers

    mcp = FastMCP("lyra-browser", instructions=instructions_for(cfg) + _UAT_INSTRUCTIONS)
    register_all(mcp, ctx)
    uat_tools.register(mcp, ctx, recorder)

    offered = set(spec.offered_tools()) | set(UAT_TOOLS)
    tools = await mcp.list_tools()
    by_name = {tool.name: tool for tool in tools}
    missing = sorted(offered - set(by_name))
    if missing:
        raise ValueError(f"tools.allow names tools this server does not have: {missing}")
    mcp.disable(keys=[tool.key for tool in tools if tool.name not in offered])

    # The capture for the trace, bypassing the middleware so it is not a step.
    shoot = by_name["screenshot"].fn

    async def capture() -> dict:
        return await shoot(full_page=False, inline=False)

    recorder.screenshot = capture

    def browser_info() -> dict[str, Any]:
        session = ctx.session
        return {
            # "shared" is the profile the run was given; "instance" is the empty one
            # the session fell back to because another browser held that profile.
            "profile_mode": getattr(session, "profile_mode", None),
            "driver": getattr(session, "active_driver", None),
            "channel": getattr(session, "active_channel", None),
            "observer_errors": list(getattr(session, "observer_errors", []) or []),
        }

    recorder.browser_info = browser_info
    # Vision is the outer layer: it attaches the image after the recorder has
    # seen — and traced — the plain result.
    if spec.limits.vision == "on_demand":
        mcp.add_middleware(VisionMiddleware())
    mcp.add_middleware(UatMiddleware(recorder))
    return mcp, ctx, recorder


def write_observations(run_dir: Path, recorder: RunRecorder) -> dict[str, Any] | None:
    """The observers' counts, written where the runner — in this process or the
    parent of a harness — reads them back for the report."""
    return recorder.write_observations()


async def serve_stdio_async(run_file: Path) -> None:
    import asyncio
    import signal

    spec, run_dir = read_run_file(run_file)
    mcp, ctx, recorder = await build_uat_server(spec, run_dir)
    # A harness that is done with us sends SIGTERM (measured: fastmcp's stdio
    # client does). Python's default handler would end the process without the
    # cleanup below, so the signal cancels the server instead.
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()

    def _interrupt(name: str) -> None:
        print(f"lyra-browser --uat-run: {name} received, closing the run", file=sys.stderr)
        if task is not None:
            task.cancel()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _interrupt, sig.name)
        except (NotImplementedError, RuntimeError):  # not a Unix main thread
            break
    try:
        await mcp.run_async()
    except asyncio.CancelledError:
        # Asked to stop: the cleanup below is the whole point of catching it,
        # and a clean exit is the right answer to the harness's signal.
        print("lyra-browser --uat-run: server stopped", file=sys.stderr)
    finally:
        recorder.write_observations()
        # The harness closed our stdin: the run is over for this browser whatever
        # the model was doing. Best effort — the process is exiting either way,
        # but a failure to close is still said out loud for the harness log.
        try:
            await ctx.session.stop()
        except Exception as exc:  # noqa: BLE001 — reported on stderr, not hidden
            print(f"lyra-browser --uat-run: closing the browser failed: {exc!r}", file=sys.stderr)


def serve_stdio(run_file: Path) -> None:
    """Entry point for ``lyra-browser --uat-run``."""
    import asyncio

    asyncio.run(serve_stdio_async(run_file))
