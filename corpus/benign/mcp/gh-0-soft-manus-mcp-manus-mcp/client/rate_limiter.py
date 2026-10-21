"""Per-endpoint rate limiter matching Manus API v2 quotas.

See: ManusAPIDocs/getting-started/rate-limits.md
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Final

# Limits per minute per endpoint key. Keys match the path suffix (e.g. "task.create").
RATE_LIMITS: Final[dict[str, int]] = {
    # Tasks
    "task.create": 10,
    "task.sendMessage": 10,
    "task.detail": 100,
    "task.list": 100,
    "task.listMessages": 100,
    "task.update": 40,
    "task.stop": 40,
    "task.delete": 40,
    "task.confirmAction": 40,
    # Projects
    "project.create": 40,
    "project.list": 100,
    # Skills
    "skill.list": 100,
    # Agents
    "agent.list": 100,
    "agent.detail": 100,
    "agent.update": 40,
    # Files
    "file.upload": 40,
    "file.detail": 100,
    "file.delete": 40,
    # Webhooks
    "webhook.create": 40,
    "webhook.list": 100,
    "webhook.delete": 40,
    "webhook.publicKey": 100,
    # Usage
    "usage.list": 600,
    "usage.teamStatistic": 600,
    "usage.teamLog": 600,
    # Connectors
    "connector.list": 100,
    # Browser
    "browser.onlineList": 100,
    # Website
    "website.status": 100,
    "website.listCheckpoints": 100,
    "website.publish": 40,
}

_WINDOW_SECONDS: Final = 60.0


@dataclass
class _Bucket:
    limit: int
    timestamps: deque[float] = field(default_factory=deque)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class RateLimiter:
    """Async sliding-window limiter. Waits locally to stay under server quotas."""

    def __init__(self, limits: dict[str, int] | None = None) -> None:
        self._limits = dict(limits or RATE_LIMITS)
        self._buckets: dict[str, _Bucket] = {}
        self._buckets_lock = asyncio.Lock()

    async def _get_bucket(self, key: str) -> _Bucket:
        limit = self._limits.get(key)
        if limit is None:
            # Unknown key: use most permissive default (100/min) but do not crash.
            limit = 100
        async with self._buckets_lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(limit=limit)
                self._buckets[key] = bucket
            return bucket

    async def acquire(self, key: str) -> None:
        """Block until a slot is available for `key` within the rolling 60s window."""
        bucket = await self._get_bucket(key)
        while True:
            async with bucket.lock:
                now = time.monotonic()
                cutoff = now - _WINDOW_SECONDS
                while bucket.timestamps and bucket.timestamps[0] <= cutoff:
                    bucket.timestamps.popleft()
                if len(bucket.timestamps) < bucket.limit:
                    bucket.timestamps.append(now)
                    return
                wait_for = _WINDOW_SECONDS - (now - bucket.timestamps[0]) + 0.01
            await asyncio.sleep(max(wait_for, 0.05))

    def note_server_429(self, key: str) -> None:
        """Call on 429 to mark the window as full so we back off locally too."""
        bucket = self._buckets.get(key)
        if bucket is None:
            return
        now = time.monotonic()
        # Fill the window so subsequent acquire() blocks briefly.
        while len(bucket.timestamps) < bucket.limit:
            bucket.timestamps.append(now)
