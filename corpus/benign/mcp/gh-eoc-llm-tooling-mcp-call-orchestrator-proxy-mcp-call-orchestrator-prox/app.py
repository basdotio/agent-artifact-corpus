"""Composition root and high-level application factory.

Wires the real backend connection, the serializing queue, and the
FastMCP proxy server together, and defines the lifespan hook that opens
the one real backend connection and starts the orchestrator's dispatcher
for the lifetime of the process. FastMCP wraps both stdio and HTTP
transports with the same lifespan manager, so this one hook covers both.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastmcp import FastMCP

from mcp_call_orchestrator_proxy.backend import QueuedMCPBackend
from mcp_call_orchestrator_proxy.client import (
    build_real_backend_client,
    resolve_backend_url,
)
from mcp_call_orchestrator_proxy.config import ProxySettings, get_settings
from mcp_call_orchestrator_proxy.exposure import (
    apply_exposure_policy,
    resolve_policies,
)
from mcp_call_orchestrator_proxy.exposure_audit import ExposureAuditBackend
from mcp_call_orchestrator_proxy.interfaces import MCPBackendClient
from mcp_call_orchestrator_proxy.orchestrator import CallOrchestrator
from mcp_call_orchestrator_proxy.resilient import (
    BackendUnavailableError,
    ResilientBackend,
)
from mcp_call_orchestrator_proxy.server import build_proxy_server

logger = logging.getLogger(__name__)


@dataclass
class ProxyApp:
    """A fully wired proxy application, ready to run."""

    mcp: FastMCP
    orchestrator: CallOrchestrator
    backend_client: MCPBackendClient


def create_proxy_app(
    settings: ProxySettings | None = None,
    backend_client: MCPBackendClient | None = None,
    backend_factory: Callable[[], MCPBackendClient] | None = None,
) -> ProxyApp:
    """Build a fully wired proxy application. Performs no I/O.

    The real backend connection is wrapped in a `ResilientBackend` so the
    proxy survives the backend being absent at startup and coming and going
    during a session.

    Backend resolution (first match wins):
    - `backend_factory`: called for each (re)connection attempt. Use this to
      simulate a backend that appears/disappears in tests.
    - `backend_client`: a single instance reused across attempts (for tests
      with a stable fake that never disconnects).
    - otherwise: a fresh real `fastmcp.Client` per attempt, built from `settings`.
    """
    settings = settings or get_settings()

    resolved_factory: Callable[[], MCPBackendClient]
    if backend_factory is not None:
        resolved_factory = backend_factory
    elif backend_client is not None:
        injected = backend_client

        def _reuse_factory() -> MCPBackendClient:
            return injected

        resolved_factory = _reuse_factory
    else:

        def _real_factory() -> MCPBackendClient:
            return build_real_backend_client(settings)

        resolved_factory = _real_factory

    resilient = ResilientBackend(
        resolved_factory,
        backend_url=resolve_backend_url(settings),
        connect_timeout=settings.connect_timeout_seconds,
        initial_backoff=settings.reconnect_initial_backoff_seconds,
        max_backoff=settings.reconnect_max_backoff_seconds,
        backoff_multiplier=settings.reconnect_backoff_multiplier,
        health_poll=settings.backend_health_poll_seconds,
    )

    orchestrator = CallOrchestrator(
        max_concurrent=settings.max_concurrent_calls,
        call_timeout=settings.call_timeout_seconds,
        # The backend being down is the one failure this proxy is built to
        # absorb, so it is a warning, not an unhandled fault. The queue itself
        # knows nothing of backends; saying so is this root's job.
        expected_errors=(BackendUnavailableError,),
    )
    queued_backend = QueuedMCPBackend(resilient, orchestrator)

    # Exposure control: resolve filter policy (pure), wrap discovery for S-4
    # audit above the queue, then apply native visibility after registration.
    resolution = resolve_policies(settings)
    audit_backend = ExposureAuditBackend(queued_backend, resolution.policies)

    @asynccontextmanager
    async def _lifespan(_server: FastMCP) -> AsyncIterator[None]:
        # `async with resilient` starts the reconnect supervisor; it does not
        # block on a down backend, so the proxy starts cleanly regardless.
        async with resilient:
            await orchestrator.start()
            try:
                yield
            finally:
                # Stop the orchestrator first (no new calls reach the backend),
                # then tear down the supervisor + live connection.
                await orchestrator.stop()

    mcp = build_proxy_server(
        lambda: audit_backend,
        server_name=settings.server_name,
        lifespan=_lifespan,
    )

    async def backend_status() -> dict[str, Any]:
        """Report whether the backend is currently reachable.

        Lets an agent check backend availability without triggering a failing
        tool call. Returns connection state, the backend URL, when it last
        connected, and the current reconnect backoff.
        """
        return resilient.status_snapshot()

    mcp.add_tool(backend_status)
    apply_exposure_policy(mcp, resolution)
    for warning in resolution.warnings:
        logger.warning("%s", warning)

    return ProxyApp(mcp=mcp, orchestrator=orchestrator, backend_client=resilient)
