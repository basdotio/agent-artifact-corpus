"""Retry policy helpers (exponential backoff with jitter)."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts_429: int = 5
    max_attempts_5xx: int = 3
    max_attempts_network: int = 2
    base_delay: float = 0.5
    max_delay: float = 30.0

    def backoff_delay(self, attempt: int, server_hint: float | None = None) -> float:
        """Return a jittered delay for `attempt` (1-indexed)."""
        if server_hint is not None and server_hint > 0:
            # Honour server hint but cap it.
            base = min(server_hint, self.max_delay)
        else:
            base = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        jitter = random.uniform(0.0, base * 0.25)
        return base + jitter


async def sleep_with_cancel(seconds: float) -> None:
    """Sleep that cooperates with asyncio cancellation."""
    if seconds <= 0:
        return
    await asyncio.sleep(seconds)
