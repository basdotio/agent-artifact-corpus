"""MCP tool ``cancel_design``: best-effort cancellation of a background selection job.

Sets the cooperative cancellation token (the pipeline stops at its next stage boundary), cancels
the asyncio task, then records the guarded ``cancelled`` transition. A job that already reached a
terminal state is never re-cancelled: the tool reports the terminal status with
``"cancelled": false`` instead of claiming success.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any

from fastmcp import Context
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool
from mcp.types import ToolAnnotations
from pydantic import Field

from src.config import TasksConfig
from src.errors import ERROR_JOB_NOT_FOUND, JobStateError
from src.tools.jobs import JobStatus, JobsStore
from src.pipeline import CancellationToken
from src.text_validation import PatternName, ensure_printable_text

logger = logging.getLogger(__name__)

_TERMINAL = (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)


class CancelDesignTool:
    """MCP tool cancelling a running background selection job."""

    def __init__(
        self,
        tasks_config: TasksConfig | None = None,
        *,
        job_tasks: dict[str, tuple[asyncio.Task[None], CancellationToken]] | None = None,
    ) -> None:
        self._tasks_config = tasks_config
        self._job_tasks = job_tasks if job_tasks is not None else {}

    @tool(
        name="cancel_design",
        description=(
            "Cancel a background design job started with submit_design_job. Best-effort: the job "
            "stops at its next stage boundary. Reports the resulting status; a job that already "
            "finished is reported as terminal with cancelled=false."
        ),
        tags={"design-patterns", "jobs"},
        annotations=ToolAnnotations(
            title="Cancel Design Job",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,  # non-idempotent: each run triggers a fresh LLM analysis
            open_world_hint=False,
        ),
    )
    async def cancel(
        self,
        job_id: Annotated[PatternName, Field(description="The job_id returned by submit_design_job.")],
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Cancel the job's task and token, then report the resulting status."""
        key = ensure_printable_text(job_id, field="job_id", allow_line_breaks=False, max_length=100)
        store = await JobsStore.get_instance()
        job = await store.get_job(key)
        if job is None:
            raise ToolError(f"{ERROR_JOB_NOT_FOUND}: Job {key!r} not found.")
        status = str(job.get("status", JobStatus.PENDING))
        if status in _TERMINAL:
            return {
                "job_id": key,
                "status": status,
                "cancelled": status == JobStatus.CANCELLED,
                "message": f"Job {key} is already in terminal state {status!r}; nothing to cancel.",
            }
        entry = self._job_tasks.get(key)
        if entry is not None:
            task, token = entry
            token.cancel()
            task.cancel()
        try:
            await store.set_cancelled(key)
            cancelled = True
        except JobStateError:
            job = await store.get_job(key)
            status = str(job.get("status")) if job is not None else "unknown"
            cancelled = status == JobStatus.CANCELLED
            if ctx is not None:
                await ctx.info(f"cancel_design: {key} already terminal ({status})")
            return {
                "job_id": key,
                "status": status,
                "cancelled": cancelled,
                "message": f"Job {key} reached terminal state {status!r} before cancellation landed.",
            }
        if ctx is not None:
            await ctx.info(f"cancel_design: {key} cancelled")
        return {
            "job_id": key,
            "status": JobStatus.CANCELLED,
            "cancelled": cancelled,
            "message": f"Job {key} cancelled at its next stage boundary; partial state discarded.",
        }


def cancel_design_tool(
    tasks_config: TasksConfig | None = None,
    *,
    job_tasks: dict[str, tuple[asyncio.Task[None], CancellationToken]] | None = None,
) -> CancelDesignTool:
    """Factory: create the ``CancelDesignTool`` instance (DP-4)."""
    return CancelDesignTool(tasks_config=tasks_config, job_tasks=job_tasks)
