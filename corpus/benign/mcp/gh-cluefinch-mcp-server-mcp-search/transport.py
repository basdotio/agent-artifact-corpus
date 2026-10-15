"""HTTPX transport with DNS validation at the actual TCP connection boundary.

Only validated numeric addresses reach the network backend. HTTP Host, TLS
SNI, certificate verification and connection-pool origins retain the hostname.
"""

import ssl
from collections.abc import AsyncIterator, Iterable, Iterator
from contextlib import contextmanager
from typing import cast

import httpcore
import httpx

from mcp_search.security import validate_url


@contextmanager
def _map_errors() -> Iterator[None]:
    try:
        yield
    except (
        httpcore.TimeoutException,
        httpcore.NetworkError,
        httpcore.ProtocolError,
        httpcore.ProxyError,
        httpcore.UnsupportedProtocol,
    ) as exc:
        error_type = getattr(httpx, type(exc).__name__, httpx.TransportError)
        raise error_type(str(exc)) from exc


class ValidatedBackend(httpcore.AsyncNetworkBackend):
    """Resolve once, reject mixed DNS answers, then connect to a checked IP."""

    def __init__(self) -> None:
        # HTTPCore's optional-import fallback obscures this public interface
        # to static analyzers. httpcore[asyncio] supplies the real backend.
        self.backend = cast(httpcore.AsyncNetworkBackend, httpcore.AnyIOBackend())

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[tuple] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        authority = f"[{host}]" if ":" in host else host
        addresses = await validate_url(f"https://{authority}:{port}/")
        numeric_hosts = sorted(address.compressed for address in addresses)
        for index, numeric_host in enumerate(numeric_hosts):
            try:
                return await self.backend.connect_tcp(
                    numeric_host,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout):
                if index == len(addresses) - 1:
                    raise
        raise httpcore.ConnectError("DNS returned no connection candidates")

    async def sleep(self, seconds: float) -> None:
        await self.backend.sleep(seconds)


class _ResponseStream(httpx.AsyncByteStream):
    def __init__(self, response: httpcore.Response) -> None:
        self.response = response

    async def __aiter__(self) -> AsyncIterator[bytes]:
        with _map_errors():
            async for chunk in self.response.aiter_stream():
                yield chunk

    async def aclose(self) -> None:
        with _map_errors():
            await self.response.aclose()


class SafeTransport(httpx.AsyncBaseTransport):
    """Adapt the public HTTPCore pool API without changing HTTPX internals."""

    def __init__(self) -> None:
        self.pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl.create_default_context(),
            network_backend=ValidatedBackend(),
            max_connections=10,
            max_keepalive_connections=10,
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if not isinstance(request.stream, httpx.AsyncByteStream):
            raise RuntimeError("SafeTransport requires an asynchronous request stream")

        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            extensions=request.extensions,
        )
        core_request.stream = request.stream
        with _map_errors():
            response = await self.pool.handle_async_request(core_request)
        return httpx.Response(
            response.status,
            headers=response.headers,
            stream=_ResponseStream(response),
            extensions=response.extensions,
        )

    async def aclose(self) -> None:
        await self.pool.aclose()
