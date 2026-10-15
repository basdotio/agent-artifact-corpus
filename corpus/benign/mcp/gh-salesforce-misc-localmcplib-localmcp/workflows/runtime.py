"""Shared lifecycle and registration for durable LangGraph runtimes."""

from __future__ import annotations

import asyncio
import os
import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Coroutine, Iterable, Mapping
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import Any, ClassVar, Protocol

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from localmcp.observability.logging import get_logger

log = get_logger(__name__)


class LeasedOperationStore[RecordT](Protocol):
    async def get(self, operation_id: str) -> RecordT | None: ...

    async def claim(self, operation_id: str, worker_id: str, *, lease_seconds: float = 90.0) -> bool: ...

    async def renew(self, operation_id: str, worker_id: str, *, lease_seconds: float = 90.0) -> bool: ...

    async def release(self, operation_id: str, worker_id: str) -> None: ...

    async def close(self) -> None: ...


class SpanTelemetry(Protocol):
    def span(
        self,
        name: str,
        *,
        observation_type: str = "span",
        metadata: Mapping[str, Any] | None = None,
        trace_seed: str | None = None,
        model: str | None = None,
    ) -> AbstractContextManager[Any]: ...


class NoopTelemetry:
    def span(
        self,
        name: str,
        *,
        observation_type: str = "span",
        metadata: Mapping[str, Any] | None = None,
        trace_seed: str | None = None,
        model: str | None = None,
    ) -> AbstractContextManager[Any]:
        return nullcontext(None)


RuntimeType = type["WorkflowRuntime[Any, Any]"]


class WorkflowRuntime[RecordT, StoreT: LeasedOperationStore[Any]](ABC):
    """Own common durable-workflow resources while domains own behavior."""

    runtime_name: ClassVar[str]
    runtime_dependencies: ClassVar[tuple[str, ...]] = ()
    state_subdirectory: ClassVar[str]
    operations_database_name: ClassVar[str] = "operations.sqlite3"
    checkpoints_database_name: ClassVar[str] = "checkpoints.sqlite3"
    recovery_interval_seconds: ClassVar[float] = 30.0
    lease_seconds: ClassVar[float] = 90.0
    heartbeat_interval_seconds: ClassVar[float] = 30.0
    _registry: ClassVar[dict[str, RuntimeType]] = {}

    def __init_subclass__(cls, *, register: bool = True, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not register:
            return
        name = cls.__dict__.get("runtime_name")
        state_subdirectory = cls.__dict__.get("state_subdirectory")
        if not isinstance(name, str) or not name:
            raise TypeError("registered workflow runtimes must declare a non-empty runtime_name")
        if not isinstance(state_subdirectory, str) or not state_subdirectory:
            raise TypeError("registered workflow runtimes must declare a non-empty state_subdirectory")
        existing = WorkflowRuntime._registry.get(name)
        if existing is not None and existing is not cls:
            raise RuntimeError(f"workflow runtime name {name!r} is already registered")
        WorkflowRuntime._registry[name] = cls

    def __init__(
        self,
        state_root: Path,
        *,
        telemetry: SpanTelemetry | None = None,
        trace_namespace: str = "localmcp",
    ):
        self.root = state_root / self.state_subdirectory
        self.store: StoreT | None = None
        self._checkpointer_cm: Any = None
        self._checkpointer: Any = None
        self.graph: Any = None
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.worker_id = str(uuid.uuid4())
        self._recovery_task: asyncio.Task[None] | None = None
        self._started = False
        self.telemetry = telemetry or NoopTelemetry()
        self.trace_namespace = trace_namespace

    @classmethod
    def registered_runtime_types(cls) -> tuple[RuntimeType, ...]:
        return tuple(WorkflowRuntime._registry.values())

    async def start(self) -> None:
        if self._started:
            return
        try:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.root.chmod(0o700)
            self.store = await self._open_store()
            self._checkpointer_cm = AsyncSqliteSaver.from_conn_string(
                os.fspath(self.root / self.checkpoints_database_name)
            )
            self._checkpointer = await self._checkpointer_cm.__aenter__()
            await self._checkpointer.setup()
            self.graph = self._build_graph(self._checkpointer)
            await self._recover()
            self._recovery_task = asyncio.create_task(self._recovery_loop())
            self._started = True
        except BaseException:
            try:
                await self.close()
            except BaseException as cleanup_error:
                log.warning(
                    "workflow.runtime_start_cleanup_failed",
                    runtime=self.runtime_name,
                    error_type=type(cleanup_error).__name__,
                )
            raise

    async def close(self) -> None:
        cleanup_errors: list[BaseException] = []
        if self._recovery_task is not None:
            self._recovery_task.cancel()
            await asyncio.gather(self._recovery_task, return_exceptions=True)
            self._recovery_task = None
        for task in self.tasks.values():
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()
        try:
            await self._close_domain_resources()
        except BaseException as exc:
            cleanup_errors.append(exc)
        if self._checkpointer_cm is not None:
            try:
                await self._checkpointer_cm.__aexit__(None, None, None)
            except BaseException as exc:
                cleanup_errors.append(exc)
            finally:
                self._checkpointer_cm = None
                self._checkpointer = None
        if self.store is not None:
            try:
                await self.store.close()
            except BaseException as exc:
                cleanup_errors.append(exc)
            finally:
                self.store = None
        self.graph = None
        self._started = False
        if cleanup_errors:
            raise cleanup_errors[0]

    def _require_store(self) -> StoreT:
        if self.store is None:
            raise self._not_started_error()
        return self.store

    def _not_started_error(self) -> Exception:
        return RuntimeError(f"{self.runtime_name} runtime is not initialized")

    def _track_task(self, operation_id: str, factory: Callable[[], Coroutine[Any, Any, None]]) -> None:
        current = self.tasks.get(operation_id)
        if current is not None and not current.done():
            return
        task = asyncio.create_task(factory())
        self.tasks[operation_id] = task

        def discard(completed: asyncio.Task[None]) -> None:
            if self.tasks.get(operation_id) is completed:
                self.tasks.pop(operation_id, None)

        task.add_done_callback(discard)

    async def _run_leased(
        self,
        operation_id: str,
        execute: Callable[[RecordT], Awaitable[None]],
    ) -> None:
        store = self._require_store()
        record = await store.get(operation_id)
        if record is None or not await store.claim(operation_id, self.worker_id, lease_seconds=self.lease_seconds):
            return
        owner_task = asyncio.current_task()
        assert owner_task is not None
        heartbeat = asyncio.create_task(self._heartbeat(operation_id, owner_task))
        try:
            with self.telemetry.span(
                f"workflow.{self.runtime_name}",
                observation_type="agent",
                metadata={"runtime": self.runtime_name, "operation_id": operation_id},
                trace_seed=f"{self.trace_namespace}:{self.runtime_name}:{operation_id}",
            ):
                await execute(record)
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            await store.release(operation_id, self.worker_id)

    async def _heartbeat(self, operation_id: str, owner_task: asyncio.Task[None]) -> None:
        store = self._require_store()
        while True:
            await asyncio.sleep(self.heartbeat_interval_seconds)
            if not await store.renew(operation_id, self.worker_id, lease_seconds=self.lease_seconds):
                owner_task.cancel()
                return

    async def _recovery_loop(self) -> None:
        while True:
            await asyncio.sleep(self.recovery_interval_seconds)
            try:
                await self._recover()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning(
                    "workflow.recovery_failed",
                    runtime=self.runtime_name,
                    error_type=type(exc).__name__,
                )

    async def _close_domain_resources(self) -> None:
        return None

    @abstractmethod
    async def _open_store(self) -> StoreT: ...

    @abstractmethod
    def _build_graph(self, checkpointer: Any) -> Any: ...

    @abstractmethod
    async def _recover(self) -> None: ...


def ordered_runtime_types(runtime_types: Iterable[RuntimeType]) -> tuple[RuntimeType, ...]:
    """Return a deterministic dependency order or fail on invalid registration."""
    by_name: dict[str, RuntimeType] = {}
    for runtime_type in runtime_types:
        name = runtime_type.runtime_name
        if name in by_name and by_name[name] is not runtime_type:
            raise RuntimeError(f"duplicate workflow runtime name {name!r}")
        by_name[name] = runtime_type
    dependencies = {name: set(runtime_type.runtime_dependencies) for name, runtime_type in by_name.items()}
    missing = sorted(
        dependency for values in dependencies.values() for dependency in values if dependency not in by_name
    )
    if missing:
        raise RuntimeError(f"workflow runtime dependencies are not registered: {', '.join(missing)}")
    ordered: list[RuntimeType] = []
    while dependencies:
        ready = sorted(name for name, values in dependencies.items() if not values)
        if not ready:
            raise RuntimeError(f"workflow runtime dependency cycle: {', '.join(sorted(dependencies))}")
        for name in ready:
            ordered.append(by_name[name])
            dependencies.pop(name)
        for values in dependencies.values():
            values.difference_update(ready)
    return tuple(ordered)
