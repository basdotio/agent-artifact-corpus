"""The tool catalog: every enabled upstream's tools under their exposed names, cached.

tools/list is answered from this cache only and never waits on an upstream. Each upstream
has its own background task that refreshes it on a short-lived connection, under its own
timeout: every refresh interval when it is healthy, with exponential backoff when it is
not. A hung upstream therefore delays only itself. Newly registered upstreams are noticed
within seconds.

Each tool also carries an effect, "read" or "write", from the gateway's reviewed policy
table and never from the upstream's own readOnlyHint. A tool with no policy row is a write
(fail closed). Policies are re-read with the registry every poll, so a change applies
within seconds; an upstream hint that contradicts a policy is logged once and ignored.

A failed refresh makes the upstream unavailable: its tools disappear until it answers
again, so clients never see stale descriptions for a server that may have changed.
"""

import logging
from dataclasses import dataclass, field, replace
from typing import Protocol

import anyio
from anyio.abc import TaskGroup, TaskStatus
from mcp.types import Tool, ToolAnnotations
from psycopg import Error as DatabaseError

from ai_gateway.pipeline.types import CatalogTool, Effect, EffectSource
from ai_gateway.proxy.naming import expose
from ai_gateway.proxy.upstream_client import UpstreamClientFactory, open_upstream_client
from ai_gateway.registry.models import UpstreamServer

logger = logging.getLogger(__name__)

_MAX_LIST_PAGES = 100
_MAX_BACKOFF_S = 60.0


class UpstreamSource(Protocol):
    async def enabled_upstreams(self) -> list[UpstreamServer]: ...

    async def tool_policies(self) -> dict[tuple[str, str], Effect]: ...


@dataclass
class _UpstreamState:
    upstream: UpstreamServer
    tools: tuple[CatalogTool, ...] = ()
    is_available: bool = False
    consecutive_failures: int = 0
    first_attempt_done: anyio.Event = field(default_factory=anyio.Event)
    stop: anyio.CancelScope = field(default_factory=anyio.CancelScope)


@dataclass(frozen=True)
class ResolvedTool:
    tool: CatalogTool
    upstream: UpstreamServer


@dataclass
class Catalog:
    source: UpstreamSource
    open_client: UpstreamClientFactory = open_upstream_client
    refresh_interval_s: float = 60.0
    registry_poll_s: float = 5.0
    """How often to look for newly registered or removed upstreams. A cheap query."""
    initial_backoff_s: float = 1.0
    """The wait after a first failed refresh; it doubles with each further failure."""
    startup_wait_s: float = 10.0
    """How long startup waits for the first refresh of each upstream before serving."""
    _states: dict[str, _UpstreamState] = field(default_factory=dict, init=False)
    _task_group: TaskGroup | None = field(default=None, init=False)
    _policies: dict[tuple[str, str], Effect] = field(default_factory=dict, init=False)
    _drift_warned: set[tuple[str, Effect, bool]] = field(default_factory=set, init=False)

    def tools(self) -> list[CatalogTool]:
        return [
            self._classified(tool) for state in self._available_states() for tool in state.tools
        ]

    def resolve(self, exposed_name: str) -> ResolvedTool | None:
        for state in self._available_states():
            for tool in state.tools:
                if tool.exposed_name == exposed_name:
                    return ResolvedTool(self._classified(tool), state.upstream)
        return None

    def _classified(self, tool: CatalogTool) -> CatalogTool:
        """The tool with its effect from the current policy table, or "write" if none covers it.

        The annotations clients see are built from that verdict alone: readOnlyHint comes
        from the effect, and the upstream's other hints (destructive, idempotent, open-world)
        and its titles are dropped, because nobody here reviewed them and a client might
        trust them.
        """
        effect = self._policies.get((tool.namespace, tool.upstream_name))
        source: EffectSource = "policy"
        if effect is None:
            effect, source = "write", "default"
        annotations = ToolAnnotations(read_only_hint=effect == "read")
        return replace(
            tool,
            tool=tool.tool.model_copy(update={"annotations": annotations, "title": None}),
            effect=effect,
            effect_source=source,
        )

    def _warn_on_drift(self, tools: tuple[CatalogTool, ...]) -> None:
        """Log, once per disagreement, an upstream hint that contradicts the policy."""
        for tool in tools:
            effect = self._policies.get((tool.namespace, tool.upstream_name))
            hint = tool.tool.annotations.read_only_hint if tool.tool.annotations else None
            if effect is None or hint is None or hint == (effect == "read"):
                continue
            key = (tool.exposed_name, effect, hint)
            if key in self._drift_warned:
                continue
            self._drift_warned.add(key)
            logger.warning(
                "tool %s: the upstream says readOnlyHint=%s but the policy says %s;"
                " using the policy",
                tool.exposed_name,
                hint,
                effect,
            )

    async def run(self, *, task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED) -> None:
        """Keep every upstream fresh, each in its own task, until cancelled.

        Reports started once every upstream has had its first refresh, or after
        startup_wait_s, so a fresh gateway usually has its catalog before the first
        request but a hung upstream cannot hold up startup.
        """
        async with anyio.create_task_group() as task_group:
            self._task_group = task_group
            try:
                await self.sync_with_registry()
                with anyio.move_on_after(self.startup_wait_s):
                    for state in list(self._states.values()):
                        await state.first_attempt_done.wait()
                task_status.started()
                while True:
                    await anyio.sleep(self.registry_poll_s)
                    await self.sync_with_registry()
            finally:
                self._task_group = None

    async def sync_with_registry(self) -> None:
        """Start a refresh task for each new or changed upstream; stop removed ones."""
        try:
            registered = await self.source.enabled_upstreams()
            self._policies = await self.source.tool_policies()
        except DatabaseError:
            # Keep serving the last known catalog and policies; the next poll tries again.
            # Letting this escape would end the background task and take the MCP endpoint
            # down with it.
            logger.warning("could not read the upstream registry; keeping the last catalog")
            return
        upstreams = {upstream.namespace: upstream for upstream in registered}

        for namespace in self._states.keys() - upstreams.keys():
            logger.info("upstream %s was removed or disabled", namespace)
            self._states.pop(namespace).stop.cancel()
        for namespace, upstream in upstreams.items():
            known = self._states.get(namespace)
            if known is not None and known.upstream == upstream:
                continue
            if known is not None:
                known.stop.cancel()
            self._start(_UpstreamState(upstream))

    def _start(self, state: _UpstreamState) -> None:
        if self._task_group is None:
            raise RuntimeError("Catalog.run() is not active")
        self._states[state.upstream.namespace] = state
        self._task_group.start_soon(self._keep_fresh, state)

    async def _keep_fresh(self, state: _UpstreamState) -> None:
        with state.stop:
            while True:
                next_refresh_in_s = await self._refresh(state)
                state.first_attempt_done.set()
                await anyio.sleep(next_refresh_in_s)

    async def _refresh(self, state: _UpstreamState) -> float:
        """Refresh one upstream under its own timeout; return seconds until the next try."""
        upstream = state.upstream
        try:
            with anyio.fail_after(upstream.connect_timeout_s + upstream.call_timeout_s):
                tools = await self._fetch_tools(upstream)
        except Exception:
            # Whatever went wrong, a server that cannot list its tools is unavailable.
            # Catching broadly is deliberate: this background task must keep running.
            state.consecutive_failures += 1
            backoff_s = min(
                _MAX_BACKOFF_S, self.initial_backoff_s * 2.0 ** (state.consecutive_failures - 1)
            )
            if state.is_available or state.consecutive_failures == 1:
                logger.warning(
                    "upstream %s is unavailable; retrying in %.0fs",
                    upstream.namespace,
                    backoff_s,
                    exc_info=True,
                )
            state.is_available = False
            state.tools = ()
            return backoff_s

        if not state.is_available:
            logger.info("upstream %s is available with %d tools", upstream.namespace, len(tools))
        self._warn_on_drift(tools)
        state.tools = tools
        state.is_available = True
        state.consecutive_failures = 0
        return self.refresh_interval_s

    async def _fetch_tools(self, upstream: UpstreamServer) -> tuple[CatalogTool, ...]:
        exposed_tools: dict[str, CatalogTool] = {}
        async with self.open_client(upstream) as client:
            cursor: str | None = None
            for _ in range(_MAX_LIST_PAGES):
                page = await client.list_tools(cursor=cursor)
                for tool in page.tools:
                    self._add_tool(exposed_tools, upstream.namespace, tool)
                cursor = page.next_cursor
                if cursor is None:
                    break
        return tuple(exposed_tools.values())

    @staticmethod
    def _add_tool(exposed_tools: dict[str, CatalogTool], namespace: str, tool: Tool) -> None:
        exposed_name = expose(namespace, tool.name)
        if exposed_name is None:
            logger.warning("skipping tool %r from %s: name cannot be exposed", tool.name, namespace)
            return
        if exposed_name in exposed_tools:
            logger.warning("skipping duplicate tool %r from %s", tool.name, namespace)
            return
        exposed_tools[exposed_name] = CatalogTool(
            namespace=namespace,
            upstream_name=tool.name,
            tool=tool.model_copy(update={"name": exposed_name}),
        )

    def _available_states(self) -> list[_UpstreamState]:
        return [state for state in self._states.values() if state.is_available]
