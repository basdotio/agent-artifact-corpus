"""Bounded request concurrency and per-host spacing, including redirects."""

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from mcp_search.config import DEFAULT_FETCH_CONCURRENCY, DEFAULT_HOST_INTERVAL
from mcp_search.security import normalize_hostname


@dataclass
class _Host:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0
    last_start: float = 0
    expiry: asyncio.TimerHandle | None = None


class RequestLimiter:
    def __init__(
        self,
        concurrency: int = DEFAULT_FETCH_CONCURRENCY,
        interval: float = DEFAULT_HOST_INTERVAL,
    ):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.interval = interval
        self.hosts: dict[str, _Host] = {}

    def _expire(self, host: str, state: _Host) -> None:
        if state.users or self.hosts.get(host) is not state:
            return
        delay = state.last_start + self.interval - time.monotonic()
        if delay > 0:
            state.expiry = asyncio.get_running_loop().call_later(
                delay, self._expire, host, state
            )
        else:
            self.hosts.pop(host, None)

    @asynccontextmanager
    async def request(self, url: str):
        host = normalize_hostname((urlsplit(url).hostname or "").rstrip("."))
        state = self.hosts.setdefault(host, _Host())
        if state.expiry is not None:
            state.expiry.cancel()
        state.users += 1
        try:
            async with state.lock:
                while (
                    delay := state.last_start + self.interval - time.monotonic()
                ) > 0:
                    await asyncio.sleep(delay)
                async with self.semaphore:
                    state.last_start = time.monotonic()
                    yield
        finally:
            state.users -= 1
            if state.users == 0:
                delay = max(0, state.last_start + self.interval - time.monotonic())
                state.expiry = asyncio.get_running_loop().call_later(
                    delay, self._expire, host, state
                )
