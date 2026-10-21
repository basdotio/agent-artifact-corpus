"""MCP tool ``submit_design_job``: start a selection run as a background job.

Returns in well under a second; the caller polls ``get_design_status``. The background task runs
the same pipeline as ``select_design_patterns`` and records its outcome through the guarded
``JobsStore`` transitions, so a cancel that wins the race is never overwritten by a late result.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from typing import Annotated, Any

from fastmcp import Context
from fastmcp.tools import tool
from mcp.types import ToolAnnotations
from pydantic import Field

from src.config import TasksConfig
from src.errors import DesignPatternError, ERROR_CANCELLED, JobStateError
from src.tools.jobs import JobStatus, JobsStore
from src.pipeline import CancellationToken, DesignPipeline
from src.tools.design import pipeline_result_to_output
from src.text_validation import PrintableText, ensure_printable_text
from src.tools._heartbeat import start_heartbeat, stop_heartbeat
from src.tools._execution import run_bounded

logger = logging.getLogger(__name__)


class SubmitDesignJobTool:
    """MCP tool starting a background selection job and returning its job id."""

    def __init__(
        self,
        pipeline: DesignPipeline,
        tasks_config: TasksConfig | None = None,
        *,
        job_tasks: dict[str, tuple[asyncio.Task[None], CancellationToken]] | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._tasks_config = tasks_config
        self._job_tasks = job_tasks if job_tasks is not None else {}

    @tool(
        name="submit_design_job",
        description=(
            "Start a background design-pattern selection job and return a job_id immediately "
            "(returns in <100 ms; the job itself takes minutes). ONLY use this when the calling "
            "client cannot wait for a long response. After starting, poll "
            "get_design_status(job_id) every 10-30 s until status is 'completed', 'failed', or "
            "'cancelled'."
        ),
        tags={"design-patterns", "jobs"},
        annotations=ToolAnnotations(
            title="Submit Design Job (async)",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    async def submit_job(
        self,
        description: Annotated[
            PrintableText,
            Field(description="The same description argument as select_design_patterns."),
        ],
        architecture_style: Annotated[str | None, Field(description="Optional architecture style hint.")] = None,
        language: Annotated[str | None, Field(description="Optional target language hint.")] = None,
        paradigm: Annotated[str | None, Field(description="Optional paradigm hint.")] = None,
        focus: Annotated[str | None, Field(description="Optional focus text.")] = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Create the job, spawn its background task and return the job id."""
        text = ensure_printable_text(description, field="description")
        params: dict[str, Any] = {
            "description": text,
            "architecture_style": architecture_style,
            "language": language,
            "paradigm": paradigm,
            "focus": focus,
        }
        store = await JobsStore.get_instance()
        job_id = await store.create_job(payload=json.dumps(params), description=text[:500])
        cancellation = CancellationToken()
        task = asyncio.create_task(
            self._run_job(job_id, params, ctx, cancellation), name=f"design-pattern-job-{job_id}"
        )
        self._job_tasks[job_id] = (task, cancellation)

        def _forget(_task: asyncio.Task[None], jid: str = job_id) -> None:
            self._job_tasks.pop(jid, None)

        task.add_done_callback(_forget)
        if ctx is not None:
            await ctx.info(f"submit_design_job: job {job_id} created")
        return {
            "job_id": job_id,
            "status": JobStatus.PENDING,
            "message": (
                f"Job {job_id} created. Poll get_design_status('{job_id}') until status is "
                "'completed', 'failed', or 'cancelled'."
            ),
        }

    async def _run_job(
        self, job_id: str, params: dict[str, Any], ctx: Context | None, cancellation: CancellationToken
    ) -> None:
        """Background task: run the pipeline and record the outcome with guarded transitions."""
        store = await JobsStore.get_instance()
        heartbeat = start_heartbeat(ctx, self._tasks_config, f"job {job_id}")
        try:
            try:
                await store.set_running(job_id)
            except JobStateError:
                logger.info("Job cancelled before it started", extra={"job_id": job_id})
                return
            if ctx is not None:
                await ctx.info(f"Job {job_id}: pipeline started")
            if await store.is_cancelled(job_id):
                return
            result = pipeline_result_to_output(
                await run_bounded(
                    self._pipeline.run_design(**params, cancellation=cancellation),
                    tasks_config=self._tasks_config,
                    operation=f"submit_design_job:{job_id}",
                )
            )
            if await store.is_cancelled(job_id):
                logger.info("Job cancelled while running; result discarded", extra={"job_id": job_id})
                return
            with suppress(JobStateError):
                await store.set_completed(job_id, json.dumps(result))
            if ctx is not None:
                await ctx.info(f"Job {job_id}: completed")
        except DesignPatternError as exc:
            if exc.code == ERROR_CANCELLED:
                with suppress(JobStateError):
                    await store.set_cancelled(job_id)
                return
            with suppress(JobStateError):
                await store.set_failed(job_id, str(exc))
            logger.warning("Job failed", extra={"job_id": job_id, "error": exc.to_dict()})
        except asyncio.CancelledError:
            with suppress(Exception):
                await store.set_cancelled(job_id)
            raise
        except Exception as exc:
            with suppress(JobStateError):
                await store.set_failed(job_id, f"ERR_999: {exc}")
            logger.error("Job crashed", extra={"job_id": job_id, "details": str(exc)})
        finally:
            stop_heartbeat(heartbeat)


def submit_design_job_tool(
    pipeline: DesignPipeline,
    tasks_config: TasksConfig | None = None,
    *,
    job_tasks: dict[str, tuple[asyncio.Task[None], CancellationToken]] | None = None,
) -> SubmitDesignJobTool:
    """Factory: create the ``SubmitDesignJobTool`` instance (DP-4)."""
    return SubmitDesignJobTool(pipeline=pipeline, tasks_config=tasks_config, job_tasks=job_tasks)
