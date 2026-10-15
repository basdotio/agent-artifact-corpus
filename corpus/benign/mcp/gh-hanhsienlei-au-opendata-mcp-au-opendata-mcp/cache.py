import hashlib
import os
import shutil
import time
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Any


class MetadataCache:
    """Small objects, short TTL, LRU by access. TTL is measured from write, so a hit
    extends an entry's position in the LRU order but never its freshness."""

    def __init__(
        self,
        max_entries: int,
        ttl_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._entries: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._max_entries = max_entries
        self._ttl = ttl_seconds
        self._clock = clock

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        written_at, value = entry
        if self._clock() - written_at > self._ttl:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        self._entries[key] = (self._clock(), value)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)


class BlobCache:
    """Materialised Parquet files under a disk budget.

    TTL uses mtime (written once). LRU eviction uses atime (touched on every read).
    Separate stat fields so a read can extend usefulness without extending freshness.
    """

    def __init__(
        self,
        root: Path,
        ttl_seconds: int,
        max_bytes: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.root = root
        self._ttl = ttl_seconds
        self._max_bytes = max_bytes
        self._clock = clock
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.parquet"

    def path_for(self, key: str) -> Path | None:
        path = self._path(key)
        if not path.exists():
            return None
        stat = path.stat()
        if self._clock() - stat.st_mtime > self._ttl:
            path.unlink(missing_ok=True)
            return None
        os.utime(path, (self._clock(), stat.st_mtime))  # touch atime only
        return path

    def store(self, key: str, source: Path) -> Path:
        dest = self._path(key)
        shutil.move(str(source), str(dest))
        now = self._clock()
        os.utime(dest, (now, now))
        self._evict()
        return dest

    def total_bytes(self) -> int:
        return sum(p.stat().st_size for p in self.root.glob("*.parquet"))

    def _evict(self) -> None:
        files = sorted(self.root.glob("*.parquet"), key=lambda p: p.stat().st_atime)
        total = sum(p.stat().st_size for p in files)
        for path in files:
            if total <= self._max_bytes:
                return
            total -= path.stat().st_size
            path.unlink(missing_ok=True)
