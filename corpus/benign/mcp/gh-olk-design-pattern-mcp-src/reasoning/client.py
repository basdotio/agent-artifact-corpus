"""
ReasoningClient: drives the ThoughtGenerator loop (draft thoughts with THIS
server's LLM, structure them via the two reasoning MCP servers) before each
pipeline phase call, per-phase strategy from ReasoningConfig.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO, TypeVar

from pydantic import BaseModel

from src.reasoning.config import (
    CODE_REASONING_EMBEDDED_CMD,
    CODE_REASONING_NPX_CMD,
    SHANNON_EMBEDDED_CMD,
    SHANNON_NPX_CMD,
    ReasoningConfig,
    ReasoningTool,
)
from src.reasoning.prompts import (
    REASONING_STEP_SYSTEM_PROMPT,
    build_step_user_prompt,
)
from src.reasoning.schemas import (
    CODE_TOOL,
    SHANNON_TOOL,
    TOOL_CONTRACTS,
    ReasoningStep,
    ReasoningTrace,
    ThoughtDraft,
    ToolContract,
    draft_to_params,
)

if TYPE_CHECKING:
    from src.agent import DesignAgent

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)

# Draft-generation callable: system/user prompt pair in, one ThoughtDraft out.
# Modeled on DesignAgent.generate_structured (single-shot structured output).
DraftGenerator = Callable[[str, str], Awaitable[ThoughtDraft]]

_THOUGHT_DRAFT_SCHEMA = ThoughtDraft

# fastmcp imports live at module scope so tests can monkeypatch
# src.reasoning.client.Client / StdioTransport with fakes.
from fastmcp import Client  # noqa: E402
from fastmcp.client.logging import LogMessage  # noqa: E402
from fastmcp.client.transports import StdioTransport  # noqa: E402

# Re-exported for tests and sibling modules (prompts capture the client's
# contract).
__all__ = [
    "CODE_TOOL",
    "SHANNON_TOOL",
    "TOOL_CONTRACTS",
    "ReasoningClient",
    "ReasoningStep",
    "ReasoningTrace",
    "ThoughtDraft",
    "ToolContract",
    "draft_to_params",
]


class BannerParseNoiseFilter(logging.Filter):
    """Drop log records emitted by the reasoning MCP servers' startup banners.

    The shannonthinking server logs "Shannon MCP Server running..." plus
    ASCII-box parse noise on stdout/stderr; code-reasoning prints
    "[info] code-reasoning MCP server running" lines. The npm servers forward these
    as ``notifications/message`` too; without the filter they would reappear in
    DEBUG logs (see ``reasoning_log_handler`` for the level policy).
    """

    _NOISE_PATTERNS = (
        "shannon mcp server running",
        "code-reasoning mcp server",
        "[info]",
        "ascii box",
        "box drawing",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage().lower()
        return not any(pattern in msg for pattern in self._NOISE_PATTERNS)


#: Logger the child servers' forwarded ``notifications/message`` records are emitted on.
#: Deliberately a child of this module's logger and not ``fastmcp.client.from_server``:
#: the ``fastmcp`` ancestor is pinned at INFO with its own RichHandlers and
#: ``propagate=False``, so a DEBUG record there would be invisible at *every*
#: ``logging_level`` — the app's own level must govern the chatter instead.
FORWARDED_LOGGER = f"{__name__}.from_server"

#: The logger object behind :data:`FORWARDED_LOGGER`, resolved once.
_forwarded_logger = logging.getLogger(FORWARDED_LOGGER)

#: MCP levels carrying the embedded reasoning servers' progress chatter: every
#: "💭 …" thinking note and both servers' startup banners arrive as
#: ``notifications/message`` at these levels. They are noise at this server's
#: default INFO level, so the receiving handler below emits them as DEBUG —
#: silent unless the operator asks for DEBUG.
_DEMOTED_MCP_LEVELS = frozenset({"info", "notice"})

#: Remaining MCP levels on the stdlib scale (parity with fastmcp's default handler:
#: ``notice`` is absent because it is demoted; ``alert``/``emergency`` are CRITICAL
#: there too; a level this map does not know stays INFO).
_MCP_LEVELS: dict[str, int] = {
    "debug": logging.DEBUG,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "alert": logging.CRITICAL,
    "emergency": logging.CRITICAL,
}


async def reasoning_log_handler(message: LogMessage) -> None:
    """Forward a child server's log notification, demoting its info chatter to DEBUG.

    Passed as ``log_handler`` to every ``Client`` this module builds. The demotion
    lives here and not in a ``logging.Filter`` on the emitting logger: the app's root
    handler carries no level of its own, so a relabelled record would still be
    emitted — only *emitting* at DEBUG keeps the chatter out of an INFO log. The
    message text keeps fastmcp's shape, so ``Received INFO from server (…)`` stays
    greppable while the record's level is DEBUG.
    """
    level = str(message.level).lower()
    level_no = (
        logging.DEBUG if level in _DEMOTED_MCP_LEVELS else _MCP_LEVELS.get(level, logging.INFO)
    )
    prefix = f"Received {message.level.upper()} from server"
    if message.logger:
        prefix += f" ({message.logger})"
    _forwarded_logger.log(level_no, f"{prefix}: {message.data}")


def _install_banner_noise_filter() -> None:
    """Silence reasoning-server banner noise on the forwarded-message logger (idempotent)."""
    target = logging.getLogger(FORWARDED_LOGGER)
    if not any(isinstance(existing, BannerParseNoiseFilter) for existing in target.filters):
        target.addFilter(BannerParseNoiseFilter())


# The shannonthinking npm server crashes with EPIPE when its stderr pipe
# closes early; keep the process handle alive via a devnull fd when quiet.
# (A one-slot list instead of a module global keeps the lazy open local to the
# helper without a `global` statement.)
_DEVNULL: list[TextIO] = []


def _devnull() -> TextIO:
    """Lazily-opened shared devnull stream for subprocess stderr routing."""
    if not _DEVNULL:
        _DEVNULL.append(open(os.devnull, "w"))  # noqa: SIM115 — process-lifetime singleton
    return _DEVNULL[0]


#: Node preload module (see src/reasoning/quiet-console.cjs, shipped beside this
#: module) that keeps the reasoning servers' stdout protocol-pure. Resolved
#: relative to the module so image, checkout and install stay in sync; when the
#: file is absent nothing is preloaded.
CONSOLE_SHIM_CANDIDATES = (str(Path(__file__).with_name("quiet-console.cjs")),)


def _subprocess_env() -> dict[str, str]:
    """Minimal env for reasoning subprocesses (NO_COLOR, non-interactive)."""
    env = dict(os.environ)
    env.pop("NO_COLOR", None)  # banners are plain text; keep default
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    # Both npm servers print informational lines with console.log/console.info,
    # i.e. on stdout, which the MCP stdio protocol owns; the python client then
    # logs an ERROR per line ("Failed to parse JSONRPC message from server").
    # The preload shim routes console output to stderr instead (see
    # docker/quiet-console.cjs); absent outside the image, then nothing changes.
    shim = next((path for path in CONSOLE_SHIM_CANDIDATES if os.path.exists(path)), None)
    if shim is not None:
        existing = env.get("NODE_OPTIONS", "").strip()
        env["NODE_OPTIONS"] = f"{existing} --require {shim}".strip()
    return env


def _extract_tool_text(result: Any) -> str:
    """Best-effort extraction of the text content blocks from a CallToolResult."""
    try:
        content = getattr(result, "content", None)
        if content is None and isinstance(result, dict):
            content = result.get("content")
        if content is None:
            return ""
        parts: list[str] = []
        for block in content:
            text = getattr(block, "text", None)
            if text is None and isinstance(block, dict):
                text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
        return "\n".join(parts)
    except Exception:  # pragma: no cover - defensive: any shape we don't know
        return ""


_PHASE_TAG_ALIASES: dict[str, str] = {
    "analyze": "problem_definition",
    "analysis": "problem_definition",
    "weights": "constraints",
    "weight": "constraints",
    "generate": "model",
    "generation": "model",
    "evaluate": "proof",
    "evaluation": "proof",
    "retry": "implementation",
    "refinement": "implementation",
    "reselection": "implementation",
    "design": "model",
    "review": "proof",
}

_DEFAULT_SHANNON_STAGE = "model"


def _coerce_shannon_stage(phase: str) -> str:
    """Map a DPML phase name onto shannonthinking's thoughtType enum."""
    tag = _PHASE_TAG_ALIASES.get(phase.strip().lower())
    if tag is None:
        logger.debug("Unknown reasoning phase %r; defaulting shannon stage to %s",
                     phase, _DEFAULT_SHANNON_STAGE)
        return _DEFAULT_SHANNON_STAGE
    return tag


#: LRU cap of the per-phase trace cache (bounded memory over a long-lived server).
_CACHE_MAX_ENTRIES = 64


class ReasoningClient:
    """Per-phase pre-LLM reasoning orchestration.

    Contract (mirrors APM):
    - Silent per-call degradation: a failed tool call yields a degraded
      ReasoningTrace, never an exception to the caller.
    - Loud health_check(): per-tool status dict.
    - ``enabled`` property honors the master switch and per-phase strategies.
    """

    def __init__(self, config: ReasoningConfig, agent: DesignAgent) -> None:
        self._config = config
        self._agent = agent
        self._trace_cache: OrderedDict[tuple[str, str, int], ReasoningTrace] = OrderedDict()
        self._inflight: dict[tuple[str, str, int], asyncio.Future[ReasoningTrace]] = {}
        self._clients: dict[str, Client[StdioTransport]] = {}
        self._closed = False
        _install_banner_noise_filter()

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    async def run_pre_llm(
        self,
        phase: str,
        context_payload: dict[str, Any],
    ) -> ReasoningTrace:
        """Run the pre-LLM reasoning loop for one phase call.

        Cacheable phases (analyze, generate) key on a payload digest; others
        always execute. Any failure inside the loop degrades silently.

        Cancellation is not a failure: it propagates as ``CancelledError`` (the job
        and request cancellation contracts depend on it), and waiters of the shared
        in-flight future are released rather than left hanging.

        A phase whose strategy is disabled returns an empty, non-degraded trace
        before the cache is consulted.
        """
        if not self.enabled or self._closed:
            return self._degraded_trace(phase, "reasoning disabled")
        strategy = self._config.get_strategy(phase)
        if not strategy.enabled:
            # A disabled phase contributes an empty context, not the degraded
            # in-prompt scaffold: no generator call, no subprocess, no cache entry.
            return ReasoningTrace(phase=phase)

        key = _cache_key(phase, context_payload)
        if key is not None:
            cached = self._trace_cache.get(key)
            if cached is not None:
                self._trace_cache.move_to_end(key)
                return cached
            joined = await self._join_in_flight(key, phase)
            if joined is not None:
                return joined
        return await self._run_loop(phase, strategy, context_payload, key)

    async def _join_in_flight(
        self,
        key: tuple[str, str, int],
        phase: str,
    ) -> ReasoningTrace | None:
        """Await the loop a co-waiting caller already runs; None means "run it yourself"."""
        inflight = self._inflight.get(key)
        if inflight is None:
            return None
        try:
            return await asyncio.shield(inflight)
        except asyncio.CancelledError:
            # A leader that was cancelled leaves no result: run the loop instead
            # of inheriting a cancellation nobody requested. Our own cancellation
            # keeps the shared future pending (shield semantics) — re-raise.
            task = asyncio.current_task()
            if not inflight.cancelled() or (task is not None and task.cancelling()):
                raise
            logger.info("Reasoning loop for phase %s rejoined after a cancelled leader", phase)
            return None

    async def _run_loop(
        self,
        phase: str,
        strategy: Any,
        context_payload: dict[str, Any],
        key: tuple[str, str, int] | None,
    ) -> ReasoningTrace:
        """One loop execution, plus the in-flight future it publishes to co-waiters."""
        future: asyncio.Future[ReasoningTrace] | None = None
        if key is not None:
            future = asyncio.get_running_loop().create_future()
            self._inflight[key] = future
        # ``trace`` stays None only while a BaseException (cancellation, shutdown)
        # unwinds: the finally block must not read an unbound local, and the
        # in-flight future it owns must be released rather than left dangling.
        trace: ReasoningTrace | None = None
        try:
            trace = await self._generate_trace(phase, strategy, context_payload)
        except asyncio.CancelledError:
            logger.info("Reasoning loop for phase %s cancelled", phase)
            raise
        except Exception as exc:  # noqa: BLE001 - degradation contract
            logger.warning("Reasoning loop for phase %s degraded: %s", phase, exc)
            trace = self._degraded_trace(
                phase, f"{type(exc).__name__}: {exc}"
            )
        finally:
            self._publish_result(key, future, trace)
        if key is not None:
            self._remember(key, trace)
        return trace

    def _publish_result(
        self,
        key: tuple[str, str, int] | None,
        future: asyncio.Future[ReasoningTrace] | None,
        trace: ReasoningTrace | None,
    ) -> None:
        """Hand the loop's result to co-waiters; None (cancellation) releases them."""
        if key is None or future is None:
            return
        popped = self._inflight.pop(key, None)
        if popped is not future or future.done():
            return
        if trace is None:
            # The loop never produced a result: fail the future instead of
            # leaving co-waiters awaiting one that can no longer resolve.
            future.cancel()
        else:
            future.set_result(trace)

    async def _generate_trace(
        self,
        phase: str,
        strategy: Any,
        context_payload: dict[str, Any],
    ) -> ReasoningTrace:
        started = time.monotonic()
        steps: list[ReasoningStep] = []
        degraded = False
        reason: str | None = None

        total_steps = min(strategy.pre_llm_thoughts, self._config.max_total_steps)
        contracts = [TOOL_CONTRACTS[t] for t in strategy.tools]

        for idx in range(total_steps):
            contract = contracts[idx % len(contracts)]
            agenda = (
                strategy.step_agenda[min(idx, len(strategy.step_agenda) - 1)]
                if strategy.step_agenda
                else "advance the phase reasoning."
            )
            prior = render_prior_steps(steps)
            user_prompt = build_step_user_prompt(
                phase=phase,
                step_number=idx + 1,
                total_steps=total_steps,
                agenda=agenda,
                system_directive=strategy.system_directive,
                context=render_context(context_payload) + prior,
            )
            try:
                draft = await self._agent.generate_structured(
                    REASONING_STEP_SYSTEM_PROMPT,
                    user_prompt,
                    _THOUGHT_DRAFT_SCHEMA,
                    operation=f"reasoning:{phase}:step:{idx + 1}",
                )
            except Exception as exc:  # noqa: BLE001
                degraded = True
                reason = f"draft generation failed at step {idx + 1}: {exc}"
                break

            revised = idx > 0 and _looks_like_revision(draft.thought)
            started_at = time.monotonic()
            try:
                output = await asyncio.wait_for(
                    self._call_tool(contract, draft, idx + 1, total_steps),
                    timeout=self._config.step_timeout_seconds,
                )
                steps.append(
                    ReasoningStep(
                        tool=contract.name,
                        thought=draft.thought,
                        phase_tag=draft.phase_tag,
                        tool_output=output,
                        revised=revised,
                        duration_ms=int((time.monotonic() - started_at) * 1000),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - per-call degradation
                degraded = True
                reason = f"tool call failed at step {idx + 1}: {exc}"
                break

        if not steps:
            degraded = True
            reason = reason or "no reasoning steps completed"

        return ReasoningTrace(
            phase=phase,
            steps=steps,
            degraded=degraded,
            degradation_reason=reason,
            total_duration_ms=int((time.monotonic() - started) * 1000),
        )

    def _build_transport(self, tool_key: str) -> StdioTransport:
        """Stdio transport for one tool; cmd resolution + quiet stderr per config."""
        command = _resolve_cmd(
            tool_key,
            self._config.shannonthinking_cmd if tool_key == SHANNON_TOOL.name else self._config.code_reasoning_cmd,
        )
        return StdioTransport(
            command=command[0],
            args=command[1:],
            env=_subprocess_env(),
            keep_alive=False,
            log_file=_devnull() if self._config.quiet_stderr else None,
        )

    async def _get_client(self, contract: ToolContract) -> Client[StdioTransport]:
        """Cached per-tool ``Client``; respawns on any prior failure.

        The step loop stays strictly sequential (no concurrent calls on one
        stdio client), so a plain dict needs no locking. Connection is bounded
        by ``spawn_timeout_seconds`` — a wedged spawn degrades the call instead
        of hanging the run. ``close()`` shuts down live clients.
        """
        client = self._clients.get(contract.name)
        if client is None:
            client = Client(
                self._build_transport(contract.name),
                log_handler=reasoning_log_handler,
            )
            try:
                await asyncio.wait_for(
                    # fastmcp 4.0.5 ships py.typed but leaves __aenter__ unannotated.
                    client.__aenter__(),  # type: ignore[no-untyped-call]
                    timeout=self._config.spawn_timeout_seconds,
                )
            except BaseException:
                # Spawn failed/timed out: close best-effort and drop the
                # half-open client so the next call starts fresh.
                with contextlib.suppress(Exception):
                    await client.close()  # type: ignore[no-untyped-call]  # fastmcp 4.0.5 leaves close unannotated
                raise
            self._clients[contract.name] = client
        return client

    async def _call_tool(
        self,
        contract: ToolContract,
        draft: ThoughtDraft,
        number: int,
        total: int,
    ) -> str:
        """One MCP round trip over the cached persistent stdio client."""
        client = await self._get_client(contract)
        phase_tag = (
            draft.phase_tag
            if contract.name == CODE_TOOL.name
            else _coerce_shannon_stage(draft.phase_tag)
        )
        payload = draft_to_params(
            _with_phase_tag(draft, phase_tag), contract, number, total
        )
        try:
            result = await client.call_tool(contract.name, payload)
        except BaseException:
            # Any transport/protocol failure invalidates the pooled client:
            # drop it so the next call respawns a fresh subprocess.
            self._clients.pop(contract.name, None)
            await client.close()  # type: ignore[no-untyped-call]  # fastmcp 4.0.5 leaves close unannotated
            raise
        return _extract_tool_text(result)

    async def health_check(self) -> dict[str, str]:
        """Per-tool status; loud (logs failures, returns statuses)."""
        statuses: dict[str, str] = {}
        checks: tuple[tuple[ReasoningTool, list[str] | str], ...] = tuple(
            (
                tool,
                self._config.shannonthinking_cmd
                if tool == "shannon"
                else self._config.code_reasoning_cmd,
            )
            for tool in self._config.active_tools()
        )
        for key, cmd in checks:
            # Config key -> MCP wire name; statuses stay keyed by the wire name.
            name = contract_name(key)
            try:
                resolved = _resolve_cmd(name, cmd)
            except Exception as exc:  # noqa: BLE001
                statuses[name] = f"unresolved: {exc}"
                logger.error("Reasoning tool %s: command unresolved: %s", name, exc)
                continue
            started = time.monotonic()
            try:
                transport = StdioTransport(
                    command=resolved[0],
                    args=resolved[1:],
                    env=_subprocess_env(),
                    keep_alive=False,
                    log_file=_devnull() if self._config.quiet_stderr else None,
                )
                async with Client(transport, log_handler=reasoning_log_handler) as client:
                    tools = await client.list_tools()
                names = {t.name for t in tools}
                if name not in names:  # ``name`` is already the wire tool name
                    raise RuntimeError(f"tool {name} not exposed")
                statuses[name] = "ok"
            except Exception as exc:  # noqa: BLE001
                statuses[name] = f"error: {type(exc).__name__}: {exc}"
                logger.error("Reasoning tool %s health check failed: %s", name, exc)
            else:
                logger.info(
                    "Reasoning tool %s healthy (%.0f ms)",
                    name,
                    (time.monotonic() - started) * 1000,
                )
        return statuses

    async def close(self) -> None:
        self._closed = True
        # Futures held by concurrent waiters resolve via asyncio.shield on the
        # awaiting side; pooled stdio clients are shut down best-effort.
        clients = list(self._clients.values())
        self._clients.clear()
        for client in clients:
            with contextlib.suppress(Exception):
                await client.close()  # type: ignore[no-untyped-call]  # fastmcp 4.0.5 leaves close unannotated

    def _remember(self, key: tuple[str, str, int], trace: ReasoningTrace) -> None:
        self._trace_cache[key] = trace
        self._trace_cache.move_to_end(key)
        while len(self._trace_cache) > _CACHE_MAX_ENTRIES:
            self._trace_cache.popitem(last=False)

    def _degraded_trace(self, phase: str, reason: str) -> ReasoningTrace:
        return ReasoningTrace(
            phase=phase,
            steps=[],
            degraded=True,
            degradation_reason=reason,
            total_duration_ms=0,
        )


def contract_name(tool_key: ReasoningTool) -> str:
    """Map the config key ('shannon'/'code') to the MCP wire tool name.

    The key space is the config ``ReasoningTool`` literal, which is what a
    strategy's ``tools`` list holds and what pydantic validates at config load —
    never a wire name like ``"code-reasoning"``.
    """
    return TOOL_CONTRACTS[tool_key].name


def _cache_key(phase: str, payload: dict[str, Any]) -> tuple[str, str, int] | None:
    """Deterministic key over phase + payload; None for uncacheable phases."""
    from src.reasoning.prompts import cacheable

    if not cacheable(phase):
        return None
    try:
        blob = repr(sorted(payload.items(), key=lambda kv: kv[0]))
    except Exception:  # pragma: no cover
        return None
    return (phase, blob, len(blob))


def _resolve_cmd(tool_key: str, cmd: list[str] | str) -> list[str]:
    """Override > embedded path > npx fallback."""
    if isinstance(cmd, str):
        cmd = [cmd]
    if cmd:
        return cmd
    if tool_key == SHANNON_TOOL.name:
        return (
            list(SHANNON_EMBEDDED_CMD)
            if os.path.exists(SHANNON_EMBEDDED_CMD[1])
            else list(SHANNON_NPX_CMD)
        )
    return (
        list(CODE_REASONING_EMBEDDED_CMD)
        if os.path.exists(CODE_REASONING_EMBEDDED_CMD[1])
        else list(CODE_REASONING_NPX_CMD)
    )


def _with_phase_tag(draft: ThoughtDraft, phase_tag: str) -> ThoughtDraft:
    if draft.phase_tag == phase_tag:
        return draft
    return draft.model_copy(update={"phase_tag": phase_tag})


def _looks_like_revision(thought: str) -> bool:
    lowered = thought.strip().lower()
    return lowered.startswith(("revise", "revised", "correction", "instead"))


def render_context(payload: dict[str, Any]) -> str:
    """Render a context payload deterministically for prompt embedding."""
    if not payload:
        return ""
    return "\n".join(f"{k}: {payload[k]}" for k in sorted(payload))


def render_prior_steps(steps: list[ReasoningStep]) -> str:
    if not steps:
        return ""
    return "\n\nPrior steps:\n" + "\n".join(
        f"- [{s.tool}/{s.phase_tag}] {s.thought}" for s in steps
    )
