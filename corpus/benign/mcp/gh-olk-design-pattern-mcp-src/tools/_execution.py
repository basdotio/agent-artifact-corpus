"""Shared whole-execution deadline for the long-running tool entrypoints.

Every long-running MCP tool and the background job runner bound one complete execution with
``tasks.deadline_seconds`` (§14). The bound is deliberately independent of the per-provider-call
timeout: a run that never settles (hanging socket, stuck sidecar, wedged reasoning subprocess)
must still terminate with a structured ``ERR_014`` instead of holding the request or the job
forever.

The helper only translates *its own* ``asyncio.timeout`` expiry. ``asyncio.CancelledError`` —
client disconnect, job cancellation, server shutdown — propagates untouched.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

from src.config import TasksConfig
from src.errors import ERROR_DEADLINE_EXCEEDED, DesignPatternError

T = TypeVar("T")


async def run_with_deadline[T](
    awaitable: Awaitable[T], *, deadline_seconds: float, operation: str
) -> T:
    """Await ``awaitable`` under a total execution budget.

    Args:
        awaitable: The operation to run; it is cancelled when the deadline expires.
        deadline_seconds: Total budget in seconds (> 0, from ``tasks.deadline_seconds``).
        operation: Logical operation label carried in the error (``ERR_014``).

    Returns:
        Whatever ``awaitable`` produced.

    Raises:
        DesignPatternError: ``ERR_014`` after the in-flight operation was cancelled.
        asyncio.CancelledError: Propagated unchanged (caller cancellation, not a deadline).
    """
    try:
        async with asyncio.timeout(deadline_seconds):
            return await awaitable
    except TimeoutError as exc:
        raise DesignPatternError(
            ERROR_DEADLINE_EXCEEDED,
            f"{operation} exceeded the {deadline_seconds:g}s execution deadline",
            hint=(
                "raise DESIGN_PATTERN_TASKS_DEADLINE_SECONDS for legitimately longer runs; "
                "a healthy run finishes well inside the default budget"
            ),
            extra={"operation": operation, "deadline_seconds": deadline_seconds},
        ) from exc


async def run_bounded[T](
    awaitable: Awaitable[T], *, tasks_config: TasksConfig | None, operation: str
) -> T:
    """Apply the configured whole-run deadline to one long-running tool/job entrypoint.

    ``tasks_config`` is ``None`` only for unit-only construction of a tool (no server config
    was injected); that keeps the direct-await behavior those callers rely on. Every wired
    entrypoint goes through the deadline.
    """
    if tasks_config is None:
        return await awaitable
    return await run_with_deadline(
        awaitable, deadline_seconds=tasks_config.deadline_seconds, operation=operation
    )
