"""Event-driven DocAgent workflow and deterministic evidence safeguards.

The citation gate establishes provenance and exact excerpt membership. It cannot
establish that an excerpt semantically entails the answer; that is the reviewer's
job and must also be evaluated against independent human labels.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


class TaskState(str, Enum):
    PENDING = "pending"
    ACTING = "acting"
    REVIEWING = "reviewing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATES = {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED}
_TRANSITIONS = {
    TaskState.PENDING: {TaskState.ACTING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.ACTING: {TaskState.REVIEWING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.REVIEWING: {
        TaskState.VALIDATING, TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED
    },
    TaskState.VALIDATING: {
        TaskState.ACTING, TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED
    },
}


def transition_state(current: TaskState, target: TaskState) -> TaskState:
    """Reject impossible and terminal-state transitions explicitly."""
    if target not in _TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid task transition: {current.value} -> {target.value}")
    return target


@dataclass(frozen=True)
class Event:
    type: str
    task_id: str
    state: str
    attempt: int = 0
    event_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: str = field(default_factory=_now)
    payload: dict[str, Any] = field(default_factory=dict, repr=False)
    metadata: dict[str, Any] = field(default_factory=dict)

    def public(self) -> dict[str, Any]:
        # Payloads can contain drafts: execution traces intentionally omit them.
        return {
            "event_id": self.event_id, "task_id": self.task_id,
            "type": self.type, "state": self.state, "attempt": self.attempt,
            "timestamp": self.timestamp, **self.metadata,
        }


class EventBus:
    """A per-task FIFO dispatcher with exactly-once delivery per event ID.

    Handlers schedule workers; they must not perform slow model/tool operations.
    In-memory deduplication is scoped to this process, not crash recovery.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._handlers: dict[str, list[Callable[[Event], Awaitable[None]]]] = defaultdict(list)
        self._seen: set[str] = set()
        self._dispatcher: asyncio.Task | None = None
        self.events: list[dict] = []
        self.duplicates = 0
        self.failure: asyncio.Future | None = None

    def subscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: Event) -> bool:
        if event.event_id in self._seen:
            self.duplicates += 1
            return False
        self._seen.add(event.event_id)
        self.events.append(event.public())
        self._queue.put_nowait(event)
        return True

    def start(self) -> None:
        if self._dispatcher is None:
            self.failure = asyncio.get_running_loop().create_future()
            self._dispatcher = asyncio.create_task(self._dispatch())

    async def _dispatch(self) -> None:
        try:
            while True:
                event = await self._queue.get()
                try:
                    for handler in self._handlers.get(event.type, ()):
                        await handler(event)
                finally:
                    self._queue.task_done()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - report arbitrary listener failures to the workflow owner
            if self.failure is not None and not self.failure.done():
                self.failure.set_result(exc)

    async def wait_idle(self) -> None:
        await self._queue.join()

    async def close(self) -> None:
        if self._dispatcher is not None:
            self._dispatcher.cancel()
            await asyncio.gather(self._dispatcher, return_exceptions=True)
            self._dispatcher = None


class WorkflowCancelled(Exception):
    pass


class ToolBudgetExceeded(Exception):
    pass


class ToolExecutionError(Exception):
    pass


READ_ONLY_TOOLS = frozenset({
    "get_outline", "search", "get_section_content", "get_image",
    "get_page_images", "get_table_image",
})


class GuardedGateway:
    """Bound calls and coalesce identical immutable reads within one run.

    Each physical attempt consumes budget, including retries. Cache hits do not.
    Separate reads can proceed concurrently. Returned results are copied so a
    caller cannot mutate the source subsequently checked by EvidenceGate.
    """

    def __init__(
        self, gateway: Any, *, timeout: float = 20, max_calls: int = 20,
        max_retries: int = 1, cancelled: asyncio.Event | None = None,
        emit: Callable[[str, dict], None] | None = None,
    ) -> None:
        if timeout <= 0 or max_calls < 1 or max_retries < 0:
            raise ValueError("Tool timeout and budget must be positive; retries must be nonnegative")
        self.gateway = gateway
        self.timeout, self.max_calls, self.max_retries = timeout, max_calls, max_retries
        self.cancelled = cancelled or asyncio.Event()
        self.emit = emit or (lambda *_: None)
        self.metrics = {
            "tool_calls": 0, "tool_requests": 0, "retries": 0,
            "cache_hits": 0, "tool_failures": 0, "tool_timeouts": 0,
        }
        self._reads: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def list_tools(self) -> list[dict]:
        self._check_cancelled()
        return await asyncio.wait_for(self.gateway.list_tools(), timeout=self.timeout)

    def _check_cancelled(self) -> None:
        if self.cancelled.is_set():
            raise WorkflowCancelled("Task cancelled")

    async def call(self, name: str, arguments: dict) -> dict:
        self._check_cancelled()
        if name not in READ_ONLY_TOOLS:
            raise ValueError(f"Tool is not an allowed read-only document tool: {name}")
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be a dictionary")
        key = json.dumps([name, arguments], sort_keys=True, ensure_ascii=False, allow_nan=False)
        self.metrics["tool_requests"] += 1
        async with self._lock:
            worker = self._reads.get(key)
            # Failures must not become permanent cached results.
            if worker is not None and worker.done() and (
                worker.cancelled() or worker.exception() is not None
            ):
                del self._reads[key]
                worker = None
            if worker is None:
                worker = asyncio.create_task(self._execute(name, copy.deepcopy(arguments)))
                self._reads[key] = worker
            else:
                self.metrics["cache_hits"] += 1
                self.emit("tool_cache_hit", {"tool": name})
        return copy.deepcopy(await asyncio.shield(worker))

    async def _execute(self, name: str, arguments: dict) -> dict:
        for attempt in range(self.max_retries + 1):
            self._check_cancelled()
            async with self._lock:
                if self.metrics["tool_calls"] >= self.max_calls:
                    raise ToolBudgetExceeded(f"Tool attempt budget exhausted ({self.max_calls})")
                self.metrics["tool_calls"] += 1
                if attempt:
                    self.metrics["retries"] += 1
            self.emit("tool_started", {"tool": name, "tool_attempt": attempt + 1})
            try:
                result = await asyncio.wait_for(
                    self.gateway.call(name, arguments), timeout=self.timeout
                )
                if not isinstance(result, dict):
                    raise TypeError("Tool result must be a dictionary")
                self.emit("tool_completed", {"tool": name, "tool_attempt": attempt + 1})
                return copy.deepcopy(result)
            except asyncio.CancelledError:
                raise
            except (ValueError, TypeError, KeyError, PermissionError) as exc:
                self.metrics["tool_failures"] += 1
                self.emit("tool_failed", {"tool": name, "error_type": type(exc).__name__})
                raise
            except Exception as exc:
                self.metrics["tool_failures"] += 1
                if isinstance(exc, TimeoutError):
                    self.metrics["tool_timeouts"] += 1
                self.emit("tool_failed", {"tool": name, "error_type": type(exc).__name__})
                if attempt == self.max_retries:
                    raise ToolExecutionError(
                        f"{name} failed after {attempt + 1} attempt(s): {type(exc).__name__}"
                    ) from exc
                self.emit("tool_retry_scheduled", {"tool": name, "tool_attempt": attempt + 2})
        raise AssertionError("Unreachable retry state")

    async def close(self) -> None:
        workers = list(self._reads.values())
        for worker in workers:
            if not worker.done():
                worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)


class _CountingGateway:
    """Instrument the unguarded baseline without changing its call policy."""

    def __init__(self, gateway: Any) -> None:
        self.gateway = gateway
        self.metrics = {"tool_calls": 0, "tool_requests": 0, "retries": 0, "cache_hits": 0}

    async def list_tools(self) -> list[dict]:
        return await self.gateway.list_tools()

    async def call(self, name: str, arguments: dict) -> dict:
        self.metrics["tool_calls"] += 1
        self.metrics["tool_requests"] += 1
        return await self.gateway.call(name, arguments)


@dataclass
class GateResult:
    valid: bool
    failures: list[str]
    evidence: list[dict]


class EvidenceGate:
    """Check reference identity and exact source excerpts, not entailment."""

    async def validate(self, answer: dict, doc_id: str, tools: Any) -> GateResult:
        failures: list[str] = []
        if not isinstance(answer, dict):
            return GateResult(False, ["answer_not_object"], [])
        if answer.get("status") not in {"answered", "insufficient"}:
            failures.append("invalid_answer_status")
        if not isinstance(answer.get("answer"), str) or not answer["answer"].strip():
            failures.append("empty_answer")
        citations = answer.get("evidence")
        if not isinstance(citations, list):
            return GateResult(False, failures + ["evidence_not_list"], [])
        if answer.get("status") == "answered" and not citations:
            failures.append("answered_without_evidence")
        validated: list[dict] = []
        for index, citation in enumerate(citations):
            prefix = f"evidence[{index}]"
            if not isinstance(citation, dict):
                failures.append(f"{prefix}:not_object")
                continue
            if citation.get("doc_id") != doc_id:
                failures.append(f"{prefix}:wrong_document")
                continue
            if type(citation.get("page")) is not int or citation["page"] < 1:
                failures.append(f"{prefix}:invalid_page")
                continue
            if any(not isinstance(citation.get(key), str) or not citation[key].strip()
                   for key in ("id", "section_id", "text")):
                failures.append(f"{prefix}:missing_reference_fields")
                continue
            source_type = citation.get("source_type")
            routes = {
                "text": ("get_section_content", "section_id"),
                "table": ("get_table_image", "table_id"),
                "image": ("get_image", "image_id"),
            }
            if source_type not in routes:
                failures.append(f"{prefix}:invalid_source_type")
                continue
            tool, parameter = routes[source_type]
            try:
                result = await tools.call(tool, {
                    "doc_id": doc_id, parameter: citation["section_id"]
                })
            except (WorkflowCancelled, ToolBudgetExceeded):
                raise
            except Exception as exc:  # noqa: BLE001 - an unavailable source must fail the citation gate
                failures.append(f"{prefix}:source_unavailable:{type(exc).__name__}")
                continue
            matching = [item for item in result.get("evidence", []) if isinstance(item, dict)
                        and all(item.get(key) == citation.get(key)
                                for key in ("id", "doc_id", "page", "section_id", "source_type"))]
            if not matching:
                failures.append(f"{prefix}:reference_identity_mismatch")
            elif not any(citation["text"] in item.get("text", "") for item in matching):
                failures.append(f"{prefix}:excerpt_not_in_source")
            else:
                validated.append(copy.deepcopy(citation))
        return GateResult(not failures, failures, validated)


class MemoryStore:
    """Document-scoped, versioned advisory memories with optional persistence."""

    def __init__(self, path: Path | str | None = None, frozen: bool = False) -> None:
        self.path = Path(path) if path is not None else None
        self.frozen = frozen
        self._records: list[dict] = []
        self.version = 0
        if self.path is not None and self.path.exists():
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if value.get("schema_version") != 1 or not isinstance(value.get("records"), list):
                raise ValueError("Unsupported memory file schema")
            self._records = value["records"]
            self.version = int(value["version"])

    def freeze(self, value: bool = True) -> MemoryStore:
        self.frozen = value
        return self

    def snapshot(self, doc_id: str, validated_only: bool = False) -> list[dict]:
        return copy.deepcopy([
            item for item in self._records if item["doc_id"] == doc_id
            and (not validated_only or item.get("validated") is True)
        ])

    def add(
        self, doc_id: str, content: str, evidence: list[dict],
        source: str, validated: bool = False,
    ) -> bool:
        if self.frozen:
            return False
        if not isinstance(content, str) or not content.strip() or not doc_id:
            return False
        content = content.strip()[:2000]
        digest = hashlib.sha256(f"{doc_id}\0{content}".encode()).hexdigest()
        if any(item["id"] == digest for item in self._records):
            return False
        if validated and not evidence:
            raise ValueError("Validated memory requires supporting evidence")
        self.version += 1
        self._records.append({
            "id": digest, "doc_id": doc_id, "content": content,
            "evidence": copy.deepcopy(evidence), "source": source,
            "validated": bool(validated), "version": self.version, "created_at": _now(),
        })
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(self.path.name + ".tmp")
            temporary.write_text(json.dumps({
                "schema_version": 1, "version": self.version, "records": self._records,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.path)
        return True


def _insufficient(reason: str) -> dict:
    return {"answer": reason, "evidence": [], "status": "insufficient"}


@dataclass
class _RunContext:
    task_id: str
    question: str
    doc_id: str
    mode: str
    bus: EventBus
    done: asyncio.Future
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)
    state: TaskState = TaskState.PENDING
    tools: Any = None
    workers: set = field(default_factory=set)
    memory: list[dict] = field(default_factory=list)
    initial_draft: dict | None = None
    draft: dict | None = None
    answer: dict | None = None
    review: dict | None = None
    correction: dict | None = None
    revisions: int = 0
    metrics: dict = field(default_factory=lambda: {
        "actor_calls": 0, "reviewer_calls": 0, "evidence_checks": 0,
        "evidence_rejections": 0, "memory_writes": 0, "stale_memories_skipped": 0,
    })
    diagnostics: list = field(default_factory=list)
    error: dict | None = None


class WorkflowEngine:
    """Actor -> Reviewer dependency graph driven by completion events.

    The caller owns the gateway's async context. A WorkflowEngine can run several
    task IDs concurrently; cancellation and tool budgets remain isolated.
    """

    def __init__(
        self, actor: Callable, reviewer: Callable, gateway: Any,
        memory_store: MemoryStore | None = None, max_revisions: int = 1,
        tool_timeout: float = 20, max_tool_calls: int = 20, max_retries: int = 1,
        agent_timeout: float = 120,
    ) -> None:
        if max_revisions < 0 or agent_timeout <= 0:
            raise ValueError("Revision bound must be nonnegative and agent timeout positive")
        if tool_timeout <= 0 or max_tool_calls < 1 or max_retries < 0:
            raise ValueError("Tool timeout and budget must be positive; retries must be nonnegative")
        self.actor, self.reviewer, self.gateway = actor, reviewer, gateway
        self.memory_store = memory_store if memory_store is not None else MemoryStore()
        self.max_revisions = max_revisions
        self.tool_timeout, self.max_tool_calls, self.max_retries = (
            tool_timeout, max_tool_calls, max_retries
        )
        self.agent_timeout = agent_timeout
        self.evidence_gate = EvidenceGate()
        self._runs: dict[str, _RunContext] = {}

    def cancel(self, task_id: str) -> bool:
        ctx = self._runs.get(task_id)
        if ctx is None or ctx.state in TERMINAL_STATES:
            return False
        ctx.cancelled.set()
        self._emit(ctx, "cancel_requested")
        return True

    def _emit(self, ctx: _RunContext, kind: str, payload: dict | None = None,
              metadata: dict | None = None) -> None:
        ctx.bus.publish(Event(kind, ctx.task_id, ctx.state.value, ctx.revisions,
                              payload=payload or {}, metadata=metadata or {}))

    def _transition(self, ctx: _RunContext, state: TaskState) -> None:
        ctx.state = transition_state(ctx.state, state)
        self._emit(ctx, "state_changed")

    def _spawn(self, ctx: _RunContext, work: Callable[[], Awaitable], completion: str) -> None:
        async def execute() -> None:
            try:
                value = await asyncio.wait_for(work(), timeout=self.agent_timeout)
                if not ctx.cancelled.is_set() and ctx.state not in TERMINAL_STATES:
                    self._emit(ctx, completion, {"value": value})
            except asyncio.CancelledError:
                raise
            except WorkflowCancelled:
                self._emit(ctx, "cancel_requested")
            except Exception as exc:  # noqa: BLE001 - arbitrary adapter failures become terminal events
                self._emit(ctx, "worker_failed", {"error": exc})
        worker = asyncio.create_task(execute())
        ctx.workers.add(worker)
        worker.add_done_callback(ctx.workers.discard)

    async def _prepare_memory(self, ctx: _RunContext) -> list[dict]:
        memories = self.memory_store.snapshot(ctx.doc_id, validated_only=ctx.mode == "optimized")
        if ctx.mode != "optimized":
            return memories
        current = []
        for item in memories:
            checked = await self.evidence_gate.validate({
                "answer": item["content"], "evidence": item["evidence"], "status": "answered"
            }, ctx.doc_id, ctx.tools)
            if checked.valid:
                current.append(item)
            else:
                ctx.metrics["stale_memories_skipped"] += 1
        return current

    async def _act(self, ctx: _RunContext) -> dict:
        if ctx.revisions == 0:
            ctx.memory = await self._prepare_memory(ctx)
        ctx.metrics["actor_calls"] += 1
        memory = copy.deepcopy(ctx.memory)
        if ctx.revisions and ctx.review is not None:
            # Ephemeral task feedback is never automatically persisted as memory.
            memory.append({
                "doc_id": ctx.doc_id, "source": "current_task_review", "validated": False,
                "content": ctx.review.get("reason", "Revise the draft using the supplied evidence."),
                "draft": copy.deepcopy(ctx.review.get("answer")),
            })
        answer = await self.actor(ctx.question, ctx.doc_id, ctx.tools, memory)
        self._validate_answer_shape(answer)
        return answer

    @staticmethod
    def _validate_answer_shape(answer: Any) -> None:
        if (not isinstance(answer, dict) or not isinstance(answer.get("answer"), str)
                or not answer["answer"].strip() or not isinstance(answer.get("evidence"), list)
                or answer.get("status") not in {"answered", "insufficient"}):
            raise ValueError("Agent must return a nonempty Answer with evidence and valid status")

    async def _review(self, ctx: _RunContext) -> dict:
        ctx.metrics["reviewer_calls"] += 1
        review = await self.reviewer(ctx.question, ctx.doc_id, copy.deepcopy(ctx.draft), ctx.tools)
        if not isinstance(review, dict) or review.get("verdict") not in {"accept", "revise", "insufficient"}:
            raise ValueError("Reviewer must return accept, revise, or insufficient")
        self._validate_answer_shape(review.get("answer"))
        if not isinstance(review.get("reason"), str):
            raise TypeError("Reviewer reason must be a string")
        if review.get("memory_candidate") is not None and not isinstance(review["memory_candidate"], str):
            raise ValueError("Memory candidate must be a string or null")
        return review

    async def _validate_review(self, ctx: _RunContext) -> GateResult:
        ctx.metrics["evidence_checks"] += 1
        return await self.evidence_gate.validate(ctx.review["answer"], ctx.doc_id, ctx.tools)

    def _finish(self, ctx: _RunContext, answer: dict) -> None:
        ctx.answer = copy.deepcopy(answer)
        self._transition(ctx, TaskState.COMPLETED)
        self._emit(ctx, "task_completed")
        if not ctx.done.done():
            ctx.done.set_result(None)

    def _legacy_memory(self, ctx: _RunContext) -> None:
        if ctx.draft["answer"] != ctx.review["answer"]["answer"]:
            candidate = ctx.review.get("memory_candidate") or ctx.review["reason"]
            wrote = self.memory_store.add(
                ctx.doc_id, candidate, ctx.review["answer"]["evidence"],
                source="legacy_unequal_answer", validated=False,
            )
            ctx.metrics["memory_writes"] += int(wrote)

    def _register_handlers(self, ctx: _RunContext) -> None:
        async def submitted(event: Event) -> None:
            if ctx.cancelled.is_set():
                await cancelled(event)
            elif ctx.state == TaskState.PENDING:
                self._transition(ctx, TaskState.ACTING)
                self._spawn(ctx, lambda: self._act(ctx), "actor_completed")

        async def actor_completed(event: Event) -> None:
            if ctx.state != TaskState.ACTING or event.attempt != ctx.revisions:
                return
            ctx.draft = event.payload["value"]
            if ctx.initial_draft is None:
                ctx.initial_draft = copy.deepcopy(ctx.draft)
            self._transition(ctx, TaskState.REVIEWING)
            self._spawn(ctx, lambda: self._review(ctx), "review_completed")

        async def review_completed(event: Event) -> None:
            if ctx.state != TaskState.REVIEWING or event.attempt != ctx.revisions:
                return
            ctx.review = event.payload["value"]
            if ctx.mode == "engineered":
                self._legacy_memory(ctx)
                self._finish(ctx, ctx.review["answer"])
            else:
                self._transition(ctx, TaskState.VALIDATING)
                self._spawn(ctx, lambda: self._validate_review(ctx), "validation_completed")

        async def validation_completed(event: Event) -> None:
            if ctx.state != TaskState.VALIDATING or event.attempt != ctx.revisions:
                return
            gate: GateResult = event.payload["value"]
            review = ctx.review
            if not gate.valid:
                ctx.metrics["evidence_rejections"] += 1
                ctx.diagnostics.append({"attempt": ctx.revisions, "gate_failures": gate.failures})
                self._emit(ctx, "evidence_rejected", metadata={"failure_count": len(gate.failures)})
            if (gate.valid and review["verdict"] == "revise"
                    and review["answer"]["status"] == "answered"
                    and review["answer"]["answer"] != ctx.draft["answer"]
                    and review.get("memory_candidate")):
                ctx.correction = {"content": review["memory_candidate"], "evidence": gate.evidence}
            needs_revision = not gate.valid or review["verdict"] == "revise"
            if needs_revision and ctx.revisions < self.max_revisions:
                ctx.revisions += 1
                if not gate.valid:
                    ctx.review = {**review, "reason": review["reason"] +
                                  " Citation verification failed: " + "; ".join(gate.failures)}
                self._transition(ctx, TaskState.ACTING)
                self._emit(ctx, "revision_requested")
                self._spawn(ctx, lambda: self._act(ctx), "actor_completed")
                return
            if not gate.valid:
                self._finish(ctx, _insufficient("无法确认：引用未通过来源核验，修订预算已用尽。"))
                return
            if review["verdict"] == "insufficient" or review["answer"]["status"] == "insufficient":
                self._finish(ctx, {**review["answer"], "status": "insufficient"})
                return
            if ctx.correction is not None:
                # Correction evidence was independently checked in this run. A
                # later accept may reuse it; failed/insufficient runs never write.
                wrote = self.memory_store.add(
                    ctx.doc_id, ctx.correction["content"], ctx.correction["evidence"],
                    source="reviewer_correction_with_source_gate", validated=True,
                )
                ctx.metrics["memory_writes"] += int(wrote)
                if wrote:
                    self._emit(ctx, "memory_updated")
            self._finish(ctx, review["answer"])

        async def failed(event: Event) -> None:
            if ctx.state in TERMINAL_STATES:
                return
            exc = event.payload["error"]
            ctx.error = {"type": type(exc).__name__, "message": str(exc)}
            ctx.answer = _insufficient("任务执行失败，未生成已确认答案。")
            self._transition(ctx, TaskState.FAILED)
            self._emit(ctx, "task_failed", metadata={"error_type": type(exc).__name__})
            if not ctx.done.done():
                ctx.done.set_result(None)

        async def cancelled(event: Event) -> None:
            if ctx.state in TERMINAL_STATES:
                return
            ctx.cancelled.set()
            ctx.answer = _insufficient("任务已取消。")
            self._transition(ctx, TaskState.CANCELLED)
            self._emit(ctx, "task_cancelled")
            for worker in list(ctx.workers):
                worker.cancel()
            if not ctx.done.done():
                ctx.done.set_result(None)

        for event_type, handler in {
            "task_submitted": submitted, "actor_completed": actor_completed,
            "review_completed": review_completed, "validation_completed": validation_completed,
            "worker_failed": failed, "cancel_requested": cancelled,
        }.items():
            ctx.bus.subscribe(event_type, handler)

    async def _baseline(self, ctx: _RunContext) -> None:
        self._transition(ctx, TaskState.ACTING)
        ctx.draft = await self._act(ctx)
        ctx.initial_draft = copy.deepcopy(ctx.draft)
        if ctx.cancelled.is_set():
            raise WorkflowCancelled("Task cancelled")
        self._transition(ctx, TaskState.REVIEWING)
        ctx.review = await self._review(ctx)
        if ctx.cancelled.is_set():
            raise WorkflowCancelled("Task cancelled")
        self._legacy_memory(ctx)
        self._finish(ctx, ctx.review["answer"])

    async def run(self, question: str, doc_id: str, mode: str = "optimized",
                  task_id: str | None = None) -> dict:
        if mode not in {"baseline", "engineered", "optimized"}:
            raise ValueError("Mode must be baseline, engineered, or optimized")
        if not question.strip() or not doc_id.strip():
            raise ValueError("Question and document ID cannot be empty")
        task_id = task_id or uuid4().hex
        if task_id in self._runs:
            raise ValueError("Task ID is already running")
        started = time.perf_counter()
        ctx = _RunContext(task_id, question, doc_id, mode, EventBus(),
                          asyncio.get_running_loop().create_future())
        self._runs[task_id] = ctx
        ctx.tools = _CountingGateway(self.gateway) if mode == "baseline" else GuardedGateway(
            self.gateway, timeout=self.tool_timeout, max_calls=self.max_tool_calls,
            max_retries=self.max_retries, cancelled=ctx.cancelled,
            emit=lambda kind, data: self._emit(ctx, kind, metadata=data),
        )
        self._register_handlers(ctx)
        # Baseline uses direct sequential calls; its bus is only a trace sink.
        try:
            if mode == "baseline":
                await asyncio.wait_for(self._baseline(ctx), timeout=2 * self.agent_timeout)
            else:
                ctx.bus.start()
                self._emit(ctx, "task_submitted")
                completed, _ = await asyncio.wait(
                    {ctx.done, ctx.bus.failure}, return_when=asyncio.FIRST_COMPLETED
                )
                if ctx.bus.failure in completed:
                    raise ctx.bus.failure.result()
        except (WorkflowCancelled, asyncio.CancelledError):
            ctx.cancelled.set()
            if ctx.state not in TERMINAL_STATES:
                self._transition(ctx, TaskState.CANCELLED)
            ctx.answer = _insufficient("任务已取消。")
            self._emit(ctx, "task_cancelled")
        except Exception as exc:  # noqa: BLE001 - top-level workflow boundary returns a structured failure
            if ctx.state not in TERMINAL_STATES:
                self._transition(ctx, TaskState.FAILED)
            ctx.error = {"type": type(exc).__name__, "message": str(exc)}
            ctx.answer = _insufficient("任务执行失败，未生成已确认答案。")
            self._emit(ctx, "task_failed", metadata={"error_type": type(exc).__name__})
        finally:
            for worker in list(ctx.workers):
                worker.cancel()
            if ctx.workers:
                await asyncio.gather(*list(ctx.workers), return_exceptions=True)
            if isinstance(ctx.tools, GuardedGateway):
                await ctx.tools.close()
            await ctx.bus.close()
            self._runs.pop(task_id, None)
        return {
            "task_id": task_id, "mode": mode, "state": ctx.state.value,
            "answer": ctx.answer, "review": ctx.review, "events": ctx.bus.events,
            "metrics": {**ctx.tools.metrics, **ctx.metrics, "revisions": ctx.revisions,
                        "duplicate_events": ctx.bus.duplicates,
                        "elapsed_seconds": round(time.perf_counter() - started, 6)},
            "diagnostics": ctx.diagnostics, "error": ctx.error,
            "evidence_gate_scope": "reference identity and exact excerpt membership; not semantic entailment",
        }
