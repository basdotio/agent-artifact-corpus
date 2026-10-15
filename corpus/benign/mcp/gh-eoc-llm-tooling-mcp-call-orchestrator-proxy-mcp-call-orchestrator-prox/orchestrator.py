"""Generic call-serialization queue.

Ensures that submitted async calls to a shared backend execute under a
controlled concurrency policy (default: fully serialized), protecting a
backend that cannot handle concurrent requests.

This component has no knowledge of MCP; it queues and runs arbitrary
zero-argument async callables.

Callers may attach a `client` and a `label` to a submission. Both are
opaque strings used only for log attribution - the queue never inspects
them, and they do not affect queuing or execution semantics. Naming the
originating client is the caller's job precisely because identifying it
*is* MCP-specific and this layer is not (see `backend.py`).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_UNKNOWN_CLIENT = "unknown"


@dataclass
class _QueuedCall[T]:
    """Internal representation of a call waiting in the queue."""

    fn: Callable[[], Awaitable[T]]
    future: asyncio.Future[T] = field(repr=False)
    enqueued_at: float = field(default_factory=time.monotonic)
    client_label: str = _UNKNOWN_CLIENT
    op_label: str = "call"


class CallOrchestrator:
    """Serializes (or bounds the concurrency of) calls to a shared backend.

    A single dispatcher task pulls queued calls in FIFO order and starts
    each one as its own task, gated by a semaphore so at most
    `max_concurrent` calls actually run at once (1 = fully serialized).
    Each call is independently subject to `call_timeout`, so a hung
    backend call cannot wedge the queue for everyone else. All public
    methods are async and safe for concurrent use by multiple callers.

    `expected_errors` are the exception types that mean "a degradation the
    proxy is absorbing by itself" rather than "a fault nobody anticipated" -
    for this project, the backend being down. They are reported at WARNING
    without a traceback; everything else keeps the full-traceback ERROR. The
    set is injected rather than hard-coded because the queue is deliberately
    ignorant of what it is queueing; the composition root knows.
    """

    def __init__(
        self,
        *,
        max_concurrent: int = 1,
        call_timeout: float = 120.0,
        expected_errors: tuple[type[BaseException], ...] = (),
    ) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")

        self._max_concurrent = max_concurrent
        self._call_timeout = call_timeout
        self._expected_errors = expected_errors

        self._queue: asyncio.Queue[_QueuedCall[Any]] = asyncio.Queue()
        self._dispatcher_task: asyncio.Task[None] | None = None
        self._inflight: set[asyncio.Task[None]] = set()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        """Start the background dispatcher. Idempotent."""
        if self._dispatcher_task is not None:
            return

        self._shutdown.clear()
        self._dispatcher_task = asyncio.create_task(
            self._dispatch_loop(), name="orchestrator-dispatcher"
        )

    async def stop(self) -> None:
        """Stop the dispatcher and any in-flight calls. Idempotent."""
        self._shutdown.set()
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._dispatcher_task
            self._dispatcher_task = None

        for task in list(self._inflight):
            task.cancel()
        for task in list(self._inflight):
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._inflight.clear()

    async def submit[T](
        self,
        fn: Callable[[], Awaitable[T]],
        *,
        label: str | None = None,
        client: str | None = None,
    ) -> T:
        """Enqueue an async call and wait for its result.

        The call executes once it reaches the front of the queue and a
        concurrency slot is available. `label` (e.g. "call_tool:echo") and
        `client` are recorded for log attribution, so an operator can read
        back which client caused which queued work, and in what order the
        queue served it. Neither affects scheduling.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[T] = loop.create_future()
        queued: _QueuedCall[T] = _QueuedCall(
            fn=fn,
            future=future,
            client_label=client or _UNKNOWN_CLIENT,
            op_label=label or "call",
        )

        await self._queue.put(queued)
        logger.info(
            "orchestrator: call accepted client=%s op=%s depth=%d",
            queued.client_label,
            queued.op_label,
            self._queue.qsize(),
        )

        try:
            return await asyncio.wait_for(future, timeout=self._call_timeout)
        except TimeoutError:
            if not future.done():
                future.cancel()
            logger.warning(
                "orchestrator: call timed out waiting for a result (client=%s op=%s)",
                queued.client_label,
                queued.op_label,
            )
            raise

    async def _dispatch_loop(self) -> None:
        """Pull queued calls in order and start each as its own task."""
        while not self._shutdown.is_set():
            try:
                queued = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except TimeoutError:
                continue

            await self._semaphore.acquire()
            task = asyncio.create_task(self._execute(queued), name="orchestrator-call")
            self._inflight.add(task)
            task.add_done_callback(self._on_call_done)

    def _on_call_done(self, task: asyncio.Task[None]) -> None:
        self._inflight.discard(task)
        self._semaphore.release()

    async def _execute(self, queued: _QueuedCall[Any]) -> None:
        """Run one queued call, independently timed out and reported."""
        queue_wait = time.monotonic() - queued.enqueued_at
        started = time.monotonic()

        # Only at DEBUG: pairs with the INFO acceptance record to separate "still
        # waiting in the queue" from "running at the backend, which has not
        # answered" - the two hangs an operator otherwise cannot tell apart.
        logger.debug(
            "orchestrator: call starting execution client=%s op=%s (waited=%.3fs)",
            queued.client_label,
            queued.op_label,
            queue_wait,
        )

        try:
            result = await asyncio.wait_for(queued.fn(), timeout=self._call_timeout)
        except TimeoutError:
            logger.error(
                "orchestrator: call timed out after %.3fs on the backend "
                "(client=%s op=%s queue_wait=%.3fs) - slot released, queue "
                "remains usable",
                time.monotonic() - started,
                queued.client_label,
                queued.op_label,
                queue_wait,
            )
            if not queued.future.done():
                queued.future.set_exception(TimeoutError("Backend call timed out"))
        except self._expected_errors as exc:
            # A degradation the proxy is absorbing (the backend is down and the
            # supervisor is already reconnecting), not a fault. WARNING, and no
            # traceback: an expected condition must not out-shout the record that
            # actually reports the outage.
            logger.warning(
                "orchestrator: call failed, backend degraded (client=%s op=%s): %s",
                queued.client_label,
                queued.op_label,
                exc,
            )
            if not queued.future.done():
                queued.future.set_exception(exc)
        except Exception as exc:
            logger.exception(
                "orchestrator: call raised an unexpected error (client=%s op=%s)",
                queued.client_label,
                queued.op_label,
            )
            if not queued.future.done():
                queued.future.set_exception(exc)
        else:
            logger.info(
                "orchestrator: call completed client=%s op=%s wait=%.3fs exec=%.3fs",
                queued.client_label,
                queued.op_label,
                queue_wait,
                time.monotonic() - started,
            )
            if not queued.future.done():
                queued.future.set_result(result)
        finally:
            self._queue.task_done()

    async def __aenter__(self) -> CallOrchestrator:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()
