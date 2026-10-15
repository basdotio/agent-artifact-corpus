"""HTTP transport that checks polling deadlines at each network read, including headers."""

from __future__ import annotations

import ipaddress
import ssl
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any
from urllib.request import getproxies

import httpcore
import httpx

_deadline: ContextVar[float | None] = ContextVar("leanwarp_deadline", default=None)


def _remaining(timeout: float | None) -> float | None:
    deadline = _deadline.get()
    if deadline is None:
        return timeout
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise httpcore.ReadTimeout("poll deadline reached")
    return remaining if timeout is None else min(timeout, remaining)


class _Stream(httpcore.NetworkStream):
    def __init__(self, stream: httpcore.NetworkStream) -> None:
        self.stream = stream

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        result = self.stream.read(max_bytes, timeout=_remaining(timeout))
        _remaining(timeout)
        return result

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        self.stream.write(buffer, timeout=_remaining(timeout))
        _remaining(timeout)

    def close(self) -> None:
        self.stream.close()

    def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore.NetworkStream:
        stream = self.stream.start_tls(ssl_context, server_hostname, _remaining(timeout))
        try:
            _remaining(timeout)
        except httpcore.TimeoutException:
            stream.close()
            raise
        return _Stream(stream)

    def get_extra_info(self, info: str) -> Any:
        return self.stream.get_extra_info(info)


class _Backend(httpcore.NetworkBackend):
    def __init__(self, backend: httpcore.NetworkBackend) -> None:
        self.backend = backend

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Any = None,
    ) -> httpcore.NetworkStream:
        stream = self.backend.connect_tcp(
            host, port, _remaining(timeout), local_address, socket_options
        )
        try:
            _remaining(timeout)
        except httpcore.TimeoutException:
            stream.close()
            raise
        return _Stream(stream)


# Keep httpcore failures in the SDK's existing HTTPX exception contract.
_ERRORS = {
    httpcore.ConnectTimeout: httpx.ConnectTimeout,
    httpcore.ReadTimeout: httpx.ReadTimeout,
    httpcore.WriteTimeout: httpx.WriteTimeout,
    httpcore.PoolTimeout: httpx.PoolTimeout,
    httpcore.ConnectError: httpx.ConnectError,
    httpcore.ReadError: httpx.ReadError,
    httpcore.WriteError: httpx.WriteError,
    httpcore.ProxyError: httpx.ProxyError,
    httpcore.UnsupportedProtocol: httpx.UnsupportedProtocol,
    httpcore.LocalProtocolError: httpx.LocalProtocolError,
    httpcore.RemoteProtocolError: httpx.RemoteProtocolError,
}


@contextmanager
def _request_context(deadline: float | None) -> Iterator[None]:
    token = _deadline.set(deadline)
    try:
        yield
    except tuple(_ERRORS) as error:
        mapped = next(target for source, target in _ERRORS.items() if isinstance(error, source))
        raise mapped(str(error)) from error
    finally:
        _deadline.reset(token)


class _ResponseStream(httpx.SyncByteStream):
    def __init__(self, response: httpcore.Response, deadline: float | None) -> None:
        self.response, self.deadline = response, deadline

    def __iter__(self) -> Iterator[bytes]:
        with _request_context(self.deadline):
            yield from self.response.iter_stream()

    def close(self) -> None:
        self.response.close()


def _environment_proxy(url: httpx.URL) -> str | None:
    """Match HTTPX's environment proxy forms for this fixed API origin."""
    proxies = getproxies()
    for entry in proxies.get("no", "").split(","):
        entry = entry.strip()
        if not entry:
            continue
        if entry == "*":
            return None
        if "://" in entry:
            pattern = httpx.URL(entry)
        else:
            try:
                address = ipaddress.ip_address(entry)
            except ValueError:
                prefix = "" if entry.lower() == "localhost" else "*"
                pattern = httpx.URL(f"all://{prefix}{entry}")
            else:
                host = f"[{address}]" if address.version == 6 else str(address)
                pattern = httpx.URL(f"all://{host}")
        if pattern.scheme not in {"all", "", url.scheme}:
            continue
        if pattern.port is not None and pattern.port != url.port:
            continue
        host = pattern.host
        if not host or host == "*":
            matches = True
        elif host.startswith("*."):
            matches = url.host.endswith(host[1:])
        elif host.startswith("*"):
            matches = url.host == host[1:] or url.host.endswith("." + host[1:])
        else:
            matches = not host or url.host == host
        if matches:
            return None
    proxy = proxies.get(url.scheme) or proxies.get("all")
    return proxy if not proxy or "://" in proxy else f"http://{proxy}"


class DeadlineTransport(httpx.BaseTransport):
    """One origin, normal TLS/environment proxies, no worker threads or private hooks.

    Deadlines are request-local even when connections are pooled. Platform DNS
    resolution and injected custom transports retain their own timeout behavior.
    """

    def __init__(
        self, origin: str, *, network_backend: httpcore.NetworkBackend | None = None
    ) -> None:
        url = httpx.URL(origin)
        proxy_url = _environment_proxy(url)
        options: dict[str, Any] = {
            "ssl_context": httpx.create_ssl_context(),
            "max_connections": 100,
            "max_keepalive_connections": 20,
            "keepalive_expiry": 5.0,
            "network_backend": _Backend(network_backend or httpcore.SyncBackend()),
        }
        self.pool: httpcore.ConnectionPool
        if proxy_url:
            proxy = httpx.Proxy(proxy_url)
            if proxy.url.scheme not in {"http", "https"}:
                raise ValueError("LeanWarp deadline transport requires an HTTP or HTTPS proxy")
            self.pool = httpcore.HTTPProxy(
                proxy_url=str(proxy.url), proxy_auth=proxy.raw_auth, **options
            )
        else:
            self.pool = httpcore.ConnectionPool(**options)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        deadline = request.extensions.get("leanwarp_deadline")
        with _request_context(deadline):
            response = self.pool.handle_request(
                httpcore.Request(
                    method=request.method,
                    url=httpcore.URL(
                        scheme=request.url.raw_scheme,
                        host=request.url.raw_host,
                        port=request.url.port,
                        target=request.url.raw_path,
                    ),
                    headers=request.headers.raw,
                    content=request.stream,
                    extensions=request.extensions,
                )
            )
        return httpx.Response(
            response.status,
            headers=response.headers,
            stream=_ResponseStream(response, deadline),
            extensions=response.extensions,
        )

    def close(self) -> None:
        self.pool.close()
