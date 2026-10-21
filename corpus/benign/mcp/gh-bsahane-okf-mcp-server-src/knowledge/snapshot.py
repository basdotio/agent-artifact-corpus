"""Published knowledge snapshots.

Layout under the data directory::

    snapshots/<id>/bundle/        OKF bundle
    snapshots/<id>/extraction/    durable extraction metadata (per source)
    snapshots/<id>/index.db       search index built from the two above
    snapshots/<id>/manifest.json  source ID -> concept, revision
    current -> snapshots/<id>     symlink, swapped atomically on publish

A request resolves `current` once and uses that snapshot throughout, so a
publish mid-request never mixes a bundle with another snapshot's index.
"""

import os
from dataclasses import dataclass
from pathlib import Path


class SnapshotError(RuntimeError):
    """Raised when no valid snapshot is published."""


@dataclass(frozen=True)
class Snapshot:
    """One immutable, published snapshot."""

    id: str
    root: Path

    @property
    def bundle(self) -> Path:
        """OKF bundle directory."""
        return self.root / "bundle"

    @property
    def extraction(self) -> Path:
        """Extraction metadata directory."""
        return self.root / "extraction"

    @property
    def index(self) -> Path:
        """Search index file (SQLite FTS5)."""
        return self.root / "index.db"

    @property
    def manifest(self) -> Path:
        """Source manifest file."""
        return self.root / "manifest.json"


def current_snapshot(data_dir: Path) -> Snapshot:
    """Resolve the published snapshot.

    Raises:
        SnapshotError: If nothing is published or `current` points outside `snapshots/`.
    """
    link = data_dir / "current"
    try:
        root = link.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as e:
        raise SnapshotError(
            "no knowledge snapshot is published; run `okf-ingest build` first"
        ) from e
    snapshots = (data_dir / "snapshots").resolve()
    if root.parent != snapshots or not (root / "bundle").is_dir():
        raise SnapshotError("the `current` snapshot link is invalid")
    return Snapshot(id=root.name, root=root)


def publish(data_dir: Path, snapshot: Snapshot) -> None:
    """Atomically point `current` at a validated snapshot."""
    tmp = data_dir / ".current.tmp"
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    tmp.symlink_to(Path("snapshots") / snapshot.id)
    os.replace(tmp, data_dir / "current")
