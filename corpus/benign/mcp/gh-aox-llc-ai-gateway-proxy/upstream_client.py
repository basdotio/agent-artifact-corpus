"""Open an MCP client connection to one upstream server."""

import os
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from importlib.metadata import version

import httpx2
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Implementation

from ai_gateway.registry.models import CREDENTIAL_ENV_SUFFIX, UpstreamServer

UpstreamClientFactory = Callable[[UpstreamServer], AbstractAsyncContextManager[Client]]

_GATEWAY_IDENTITY = Implementation(name="ai-gateway", version=version("ai-gateway"))


class UpstreamCredentialError(RuntimeError):
    """The upstream needs a service credential that this process does not have.

    The message names the environment variable, never its value.
    """


def upstream_headers(upstream: UpstreamServer) -> dict[str, str]:
    """The headers every connection to this upstream carries: its service credential, if any.

    Only variables whose name ends in _SERVICE_TOKEN are read. The credential is read from
    the environment at connect time, so rotating it needs a
    restart of the gateway but no registry change. A missing or empty variable makes the
    upstream unavailable rather than letting the gateway call it without credentials.
    """
    if upstream.credential_env is None:
        return {}
    if not upstream.credential_env.endswith(CREDENTIAL_ENV_SUFFIX):
        # The registry's own constraint forbids this; check again here so a row written
        # around it still cannot make the gateway send some other secret to an upstream.
        raise UpstreamCredentialError(
            f"upstream {upstream.namespace!r} names {upstream.credential_env} as its credential,"
            f" but only variables ending in {CREDENTIAL_ENV_SUFFIX} may be used; refusing"
        )
    value = os.environ.get(upstream.credential_env, "")
    if not value:
        raise UpstreamCredentialError(
            f"upstream {upstream.namespace!r} needs the service credential in the environment"
            f" variable {upstream.credential_env}, which is not set"
        )
    return {"Authorization": f"Bearer {value}"}


@asynccontextmanager
async def open_upstream_client(upstream: UpstreamServer) -> AsyncGenerator[Client]:
    """Connect over Streamable HTTP, pinned to the handshake protocol (2025-11-25).

    The SDK's response cache is off: the catalog must always see the upstream's
    current tool list, never a cached one.
    """
    timeout = httpx2.Timeout(upstream.call_timeout_s, connect=upstream.connect_timeout_s)
    async with (
        httpx2.AsyncClient(
            timeout=timeout, follow_redirects=False, headers=upstream_headers(upstream)
        ) as http_client,
        Client(
            streamable_http_client(upstream.url, http_client=http_client),
            read_timeout_seconds=upstream.call_timeout_s,
            mode="legacy",
            cache=None,
            client_info=_GATEWAY_IDENTITY,
        ) as client,
    ):
        yield client
