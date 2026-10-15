import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

T = TypeVar("T")
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


async def with_retry(
    factory: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay: float = 0.5,
) -> T:
    """Retry transient HTTP errors with exponential backoff and jitter."""
    for attempt in range(retries + 1):
        try:
            return await factory()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in RETRYABLE_STATUS or attempt == retries:
                raise
            retry_after = exc.response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else base_delay * 2**attempt
            except ValueError:
                delay = base_delay * 2**attempt
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt == retries:
                raise
            delay = base_delay * 2**attempt
        await asyncio.sleep(delay + random.uniform(0, 0.25))
    raise RuntimeError("retry loop exited unexpectedly")
