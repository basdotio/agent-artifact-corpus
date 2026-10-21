"""Shared heartbeat helper for long-running tool calls.

A client's idle timer must not fire while a pipeline run is in flight, so long tools drive a
parallel coroutine that reports progress. Kept in one place so every tool uses the same cadence.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastmcp import Context

from src.config import TasksConfig

logger = logging.getLogger(__name__)


def start_heartbeat(
    ctx: Context | None, tasks_config: TasksConfig | None, label: str
) -> asyncio.Task[None] | None:
    """Start progress notifications for a long call; ``None`` when disabled or context-free."""
    if ctx is None or tasks_config is None or not tasks_config.heartbeat_enabled:
        return None

    interval = tasks_config.heartbeat_interval_seconds

    async def _heartbeat() -> None:
        step = 0
        try:
            while True:
                await asyncio.sleep(interval)
                step += 1
                with contextlib.suppress(Exception):
                    await ctx.report_progress(progress=step, message=f"{label} in progress")
        except asyncio.CancelledError:
            pass

    return asyncio.create_task(_heartbeat())


def stop_heartbeat(task: asyncio.Task[None] | None) -> None:
    """Cancel a heartbeat task started by :func:`start_heartbeat`."""
    if task is not None:
        task.cancel()
