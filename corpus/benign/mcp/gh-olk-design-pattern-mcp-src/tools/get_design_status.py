"""MCP tool ``get_design_status``: poll a background selection job.

Pure read: the stored status, timestamps and — once the job completed — the ``DesignResult``
payload, or the error text when it failed. An unknown job id is a ``ToolError`` (``ERR_404``).
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastmcp import Context
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool
from mcp.types import ToolAnnotations
from pydantic import Field

from src.config import TasksConfig
from src.errors import ERROR_JOB_NOT_FOUND
from src.tools.jobs import JobStatus, JobsStore
from src.text_validation import PatternName, ensure_printable_text

logger = logging.getLogger(__name__)

_STATUS_MESSAGES: dict[str, str] = {
    JobStatus.PENDING: "Job is queued; poll again in 10-30 s.",
    JobStatus.RUNNING: "Job is running; poll again in 10-30 s.",
    JobStatus.COMPLETED: "Job completed; the result field carries the DesignResult payload.",
    JobStatus.FAILED: "Job failed; the error field carries the structured failure.",
    JobStatus.CANCELLED: "Job was cancelled; its partial state was discarded.",
}


class GetDesignStatusTool:
    """MCP tool returning the status (and result) of a background selection job."""

    def __init__(self, tasks_config: TasksConfig | None = None) -> None:
        self._tasks_config = tasks_config

    @tool(
        name="get_design_status",
        description=(
            "Poll the status of a background design job started with submit_design_job. Returns "
            "job_id, status ('pending'|'running'|'completed'|'failed'|'cancelled'), a message and "
            "the timestamps; 'result' when completed, 'error' when failed."
        ),
        tags={"design-patterns", "jobs"},
        annotations=ToolAnnotations(
            title="Get Design Status",
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def get_status(
        self,
        job_id: Annotated[PatternName, Field(description="The job_id returned by submit_design_job.")],
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Return the stored job row (with the decoded result when completed)."""
        key = ensure_printable_text(job_id, field="job_id", allow_line_breaks=False, max_length=100)
        store = await JobsStore.get_instance()
        job = await store.get_job(key)
        if job is None:
            raise ToolError(f"{ERROR_JOB_NOT_FOUND}: Job {key!r} not found.")
        status = str(job.get("status", JobStatus.PENDING))
        payload: dict[str, Any] = {
            "job_id": key,
            "status": status,
            "message": _STATUS_MESSAGES.get(status, "Unknown job status."),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
        }
        if status == JobStatus.COMPLETED and job.get("result"):
            try:
                payload["result"] = json.loads(str(job["result"]))
            except json.JSONDecodeError as exc:
                logger.error("Stored job result is not valid JSON", extra={"job_id": key, "details": str(exc)})
                payload["error"] = f"ERR_999: stored result is not valid JSON: {exc}"
        if status == JobStatus.FAILED and job.get("error"):
            payload["error"] = str(job["error"])
        if ctx is not None:
            await ctx.info(f"get_design_status: {key} -> {status}")
        return payload


def get_design_status_tool(tasks_config: TasksConfig | None = None) -> GetDesignStatusTool:
    """Factory: create the ``GetDesignStatusTool`` instance (DP-4)."""
    return GetDesignStatusTool(tasks_config=tasks_config)
