"""Stopping background tasks reliably.

Shared by the sibling servers, byte for byte. Change it in mcp-server-shared,
not in a copy, then sync (`python scripts/sync_shared.py --update`).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

log = logging.getLogger(__name__)


async def stop_task(task: asyncio.Task[Any] | None, timeout: float, what: str) -> None:
    """Cancel a background task and wait until it has finished, re-cancelling as needed, for at most `timeout`.

    Why not just `task.cancel(); await task`:
    - One cancel isn't always enough. On Python 3.11, asyncio.wait_for can return the awaited result and
      drop a cancellation that arrives in the same loop iteration (CPython PR #28149; fixed in 3.12). The
      task carries on, and awaiting it hangs shutdown forever. So: cancel, wait briefly, cancel again until
      it's done.
    - Bounded: a task that still won't exit is abandoned with a warning rather than hanging the server.
    - `asyncio.wait` never raises the task's own CancelledError into us, so a cancellation of *our*
      caller still propagates (suppressing CancelledError around `await task` swallowed both).
    """
    if task is None:
        return
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not task.done():
        left = deadline - loop.time()
        if left <= 0:
            log.warning("%s didn't stop within %.0fs; abandoning it", what, timeout)
            return
        task.cancel()
        await asyncio.wait({task}, timeout=min(0.25, left))
    if not task.cancelled() and task.exception() is not None:
        log.debug("%s ended with %r", what, task.exception())
