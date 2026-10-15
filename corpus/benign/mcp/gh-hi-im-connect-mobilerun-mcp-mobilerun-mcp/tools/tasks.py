"""Agent tasks: run_task and the task tools of droidrun's official MCP, plus macro replay.

A task on a Mobilerun Cloud device goes to the cloud tasks API (tools/cloud.py). A task on a
local device runs the mobilerun CLI agent (`mobilerun run`) as a background process; its id is
``local-<n>`` and get_task / list_tasks / stop_task / get_task_media accept either kind.
"""

from __future__ import annotations

import asyncio
import io
import json
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from ..errors import fail
from ..session import Runtime
from ..targets import CLOUD, resolve_target
from . import cloud
from .common import Device
from .legacy import GOAL, _mobilerun_bin

TASK_ROOT = Path(tempfile.gettempdir()) / "mobilerun-mcp" / "tasks"
RUN_TIMEOUT = 1800.0
OUTPUT_TAIL = 4000


@dataclass
class LocalTask:
    id: str
    device: str
    task: str
    folder: Path
    started: float
    proc: asyncio.subprocess.Process | None = None
    output: list[str] = field(default_factory=list)
    status: str = "running"
    finished: float | None = None
    result: str = ""

    def text(self) -> str:
        return "".join(self.output)

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "deviceId": self.device,
            "task": self.task,
            "status": self.status,
            "succeeded": self.status == "completed" and self.result.startswith("Goal achieved"),
            "result": self.result,
            "createdAt": self.started,
            "finishedAt": self.finished,
            "trajectory_folder": str(self.trajectory() or ""),
        }

    def trajectory(self) -> Path | None:
        folders = sorted((self.folder / "trajectories").glob("*"))
        return folders[-1] if folders else None


class LocalTasks:
    def __init__(self) -> None:
        self.tasks: dict[str, LocalTask] = {}
        self._n = 0

    def new(self, device: str, task: str) -> LocalTask:
        self._n += 1
        tid = f"local-{self._n}-{int(time.time())}"
        folder = TASK_ROOT / tid
        folder.mkdir(parents=True, exist_ok=True)
        entry = LocalTask(tid, device, task, folder, time.time())
        self.tasks[tid] = entry
        return entry

    def get(self, tid: str) -> LocalTask:
        if tid not in self.tasks:
            fail("element_not_found", f"no task {tid}", "list_tasks shows the known ones")
        return self.tasks[tid]


async def _pump(entry: LocalTask) -> None:
    assert entry.proc is not None and entry.proc.stdout is not None
    try:
        while line := await entry.proc.stdout.readline():
            entry.output.append(line.decode("utf-8", "replace"))
        code = await entry.proc.wait()
    except asyncio.CancelledError:
        entry.proc.kill()
        raise
    found = GOAL.findall(entry.text())
    entry.result = found[-1] if found else ""
    if entry.status != "cancelled":
        entry.status = "completed" if code == 0 else "failed"
    entry.finished = time.time()


def _is_cloud(device: str | None) -> bool:
    return bool(device) and resolve_target(device).kind == CLOUD


def register(mcp: FastMCP, rt: Runtime) -> None:
    local = LocalTasks()
    rt.local_tasks = local

    @mcp.tool(tags={"write"})
    async def run_task(
        task: str,
        deviceId: str | None = None,
        llmModel: str | None = None,
        maxSteps: int | None = None,
        vision: bool | None = None,
        reasoning: bool = False,
        stealth: bool | None = None,
        outputSchema: dict | None = None,
        apps: list | None = None,
        credentials: list | None = None,
        files: list | None = None,
        wait: bool = True,
        steps: int | None = None,
        device: Device = None,
    ) -> dict:
        """Hand a natural-language goal to the Mobilerun agent. On a Mobilerun Cloud device it
        runs in the cloud (llmModel, maxSteps, vision, stealth, outputSchema, apps, credentials,
        files) and returns the task; poll get_task. On a local device it runs the mobilerun CLI
        agent (llmModel, maxSteps, vision, reasoning); wait=true blocks until it finishes,
        wait=false returns a local-* task id for get_task / stop_task. The agent's self-report
        can be wrong: verify on screen. Disabled while the safety policy is on."""
        if rt.config.policy != "off":
            fail(
                "policy_blocked",
                "run_task acts on its own and cannot be policed",
                "use step-by-step tools",
            )
        target = deviceId or device
        if _is_cloud(target):
            return await cloud.cloud_run_task(
                rt,
                deviceId=resolve_target(target).id,
                task=task,
                llmModel=llmModel,
                maxSteps=maxSteps or steps,
                outputSchema=outputSchema,
                stealth=stealth,
                vision=vision,
                apps=apps,
                credentials=credentials,
                files=files,
            )
        session = rt.session(target)
        if not session.has_adb:
            fail(
                "unsupported",
                "the local mobilerun agent needs an adb device; use a cloud device id",
            )
        ignored = [
            n
            for n, v in (
                ("outputSchema", outputSchema),
                ("apps", apps),
                ("credentials", credentials),
                ("files", files),
                ("stealth", stealth),
            )
            if v
        ]
        entry = local.new(session.serial, task)
        args = [
            "run",
            "-d",
            session.serial,
            "--steps",
            str(maxSteps or steps or 15),
            "--save-trajectory",
            "action",
        ]
        if llmModel:
            args += ["-m", llmModel]
        if vision:
            args.append("--vision")
        if reasoning:
            args.append("--reasoning")
        entry.proc = await asyncio.create_subprocess_exec(
            _mobilerun_bin(rt.config.mobilerun_bin),
            *args,
            task,
            cwd=entry.folder,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        pump = asyncio.create_task(_pump(entry))
        note = {"ignored_locally": ignored} if ignored else {}
        if not wait:
            return {"ok": True, "taskId": entry.id, "status": "running", **note}
        try:
            await asyncio.wait_for(asyncio.shield(pump), RUN_TIMEOUT)
        except TimeoutError:
            entry.status = "cancelled"
            entry.proc.kill()
            fail("timeout", f"agent exceeded {RUN_TIMEOUT:.0f}s", f"task {entry.id} was stopped")
        return {
            "ok": entry.status == "completed",
            "taskId": entry.id,
            "result": entry.result,
            "output_tail": entry.text()[-OUTPUT_TAIL:],
            "note": "agent self-report; verify with perceive_screen",
            **note,
        }

    @mcp.tool(tags={"read"})
    async def get_task(
        taskId: str, view: str = "summary", offset: int | None = None, limit: int | None = None
    ) -> dict:
        """A task's summary, status or trajectory (view). Trajectories are paged (offset, limit)."""
        if view not in ("summary", "status", "trajectory"):
            fail("invalid_argument", "view must be summary, status or trajectory")
        if not taskId.startswith("local-"):
            return await cloud.cloud_get_task(rt, taskId, view=view, offset=offset, limit=limit)
        entry = local.get(taskId)
        if view == "status":
            return {"id": entry.id, "status": entry.status}
        if view == "summary":
            return {**entry.summary(), "output_tail": entry.text()[-OUTPUT_TAIL:]}
        folder = entry.trajectory()
        path = folder / "trajectory.json" if folder else None
        if path is None or not path.is_file():
            return {"id": entry.id, "events": [], "total": 0, "status": entry.status}
        events = json.loads(path.read_text())
        events = events if isinstance(events, list) else events.get("events", [])
        start, count = offset or 0, limit or 50
        return {
            "id": entry.id,
            "total": len(events),
            "offset": start,
            "events": events[start : start + count],
        }

    @mcp.tool(tags={"read"})
    async def list_tasks(
        deviceId: str | None = None,
        status: str | None = None,
        query: str | None = None,
        orderBy: str | None = None,
        orderByDirection: str | None = None,
        page: int | None = None,
        pageSize: int | None = None,
        scope: str = "all",
    ) -> dict:
        """Tasks: local agent runs of this server, plus Mobilerun Cloud tasks when
        MOBILERUN_CLOUD_API_KEY is set (scope: local | cloud | all)."""
        out: dict[str, Any] = {}
        if scope in ("local", "all"):
            items = [t.summary() for t in local.tasks.values()]
            items = [
                t
                for t in items
                if (not deviceId or t["deviceId"] == deviceId)
                and (not status or t["status"] == status)
                and (not query or query.lower() in t["task"].lower())
            ]
            out["local"] = items
        if scope in ("cloud", "all") and (scope == "cloud" or rt.config.cloud_api_key):
            out["cloud"] = await cloud.cloud_list_tasks(
                rt,
                deviceId=deviceId,
                orderBy=orderBy,
                orderByDirection=orderByDirection,
                page=page,
                pageSize=pageSize,
                query=query,
                status=status,
            )
        return out

    @mcp.tool(tags={"write"})
    async def stop_task(taskId: str) -> dict:
        """Stop a running task."""
        if not taskId.startswith("local-"):
            return await cloud.cloud_stop_task(rt, taskId)
        entry = local.get(taskId)
        if entry.proc is not None and entry.proc.returncode is None:
            entry.status = "cancelled"
            entry.proc.terminate()
        return {"ok": True, "id": entry.id, "status": entry.status}

    @mcp.tool(tags={"read"})
    async def get_task_media(taskId: str, kind: str = "screenshot", index: int | None = None):
        """A screenshot (or ui_state) the task recorded; index picks the step (default latest)."""
        if kind not in ("screenshot", "ui_state"):
            fail("invalid_argument", "kind must be screenshot or ui_state")
        if not taskId.startswith("local-"):
            return await cloud.cloud_get_task_media(rt, taskId, kind=kind, index=index)
        folder = local.get(taskId).trajectory()
        if folder is None:
            fail("element_not_found", "the task has not recorded anything yet")
        if kind == "ui_state":
            path = folder / "trajectory.json"
            data = json.loads(path.read_text()) if path.is_file() else {}
            states = data.get("ui_states", []) if isinstance(data, dict) else []
            if not states:
                fail("element_not_found", "no ui_state recorded for this task")
            return states[index if index is not None else -1]
        gif = folder / "screenshots" / "trajectory.gif"
        pngs = (
            sorted((folder / "screenshots").glob("*.png"))
            if (folder / "screenshots").is_dir()
            else []
        )
        if pngs:
            return Image(data=pngs[index if index is not None else -1].read_bytes(), format="png")
        if not gif.is_file():
            fail("element_not_found", "no screenshots recorded for this task")
        from PIL import Image as PILImage

        frames = PILImage.open(gif)
        total = getattr(frames, "n_frames", 1)
        frames.seek((index if index is not None else total - 1) % total)
        buf = io.BytesIO()
        frames.convert("RGB").save(buf, format="PNG")
        return Image(data=buf.getvalue(), format="png")

    @mcp.tool(tags={"write"})
    async def send_task_message(taskId: str, message: str) -> dict:
        """Send a message to a running cloud task (e.g. answer its question)."""
        if taskId.startswith("local-"):
            fail(
                "unsupported",
                "local mobilerun CLI tasks do not take messages",
                "stop_task and run a new task",
            )
        return await cloud.cloud_send_task_message(rt, taskId, message)

    async def cli(*args: str, timeout: float = 600.0) -> dict:
        proc = await asyncio.create_subprocess_exec(
            _mobilerun_bin(rt.config.mobilerun_bin),
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            fail("timeout", f"mobilerun {args[0]} {args[1]} exceeded {timeout:.0f}s")
        text = out.decode("utf-8", "replace")
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "output": re.sub(r"\x1b\[[0-9;]*m", "", text)[-OUTPUT_TAIL:],
        }

    @mcp.tool(tags={"read"})
    async def macro_list(directory: str | None = None) -> dict:
        """Recorded trajectories (mobilerun macro list); defaults to this server's task folder."""
        return await cli("macro", "list", str(directory or TASK_ROOT), timeout=60)

    @mcp.tool(tags={"write"})
    async def macro_replay(
        path: str,
        delay: float | None = None,
        start_from: int | None = None,
        max_steps: int | None = None,
        dry_run: bool = False,
        on_mismatch: str = "stop",
        device: Device = None,
    ) -> dict:
        """Replay a recorded macro (macro.json or a trajectory folder) on the device
        (mobilerun macro replay). on_mismatch: stop | agent."""
        if on_mismatch not in ("stop", "agent"):
            fail("invalid_argument", "on_mismatch must be stop or agent")
        session = rt.session(device)
        args = ["macro", "replay", path, "-d", session.serial, "--on-mismatch", on_mismatch]
        if delay is not None:
            args += ["-t", str(delay)]
        if start_from is not None:
            args += ["-s", str(start_from)]
        if max_steps is not None:
            args += ["-m", str(max_steps)]
        if dry_run:
            args.append("--dry-run")
        return await cli(*args)
