"""Mirror remote sources into a local folder that `okf-ingest build` reads.

A connector lists `RemoteItem`s (path, version, principals) and downloads
content. `sync()` makes the mirror match the source exactly:

- unchanged items (same version) are not downloaded again;
- changed items are downloaded to a temporary file and moved into place;
- items gone from the source are deleted from the mirror;
- `.okf/access.json` is rewritten with every item's principals, so
  permission changes and revocations reach the next build.

Remote names are sanitized so no path can escape the mirror.
"""

import json
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, Dict, Iterable, List, Optional

import httpx

from okf_mcp_server.src.ingest.extract import SUPPORTED_SUFFIXES

STATE_FILE = ".okf/state.json"
ACCESS_FILE = ".okf/access.json"
MAX_FILE_BYTES = 200 * 1024 * 1024


@dataclass
class RemoteItem:
    """One file in a source system."""

    key: str  # stable ID in the source (item ID, path, …)
    path: str  # source-relative POSIX path, as the source names it
    version: str  # changes whenever content changes (eTag, md5, mtime+size)
    size: Optional[int] = None
    principals: Optional[List[str]] = None  # None: no source permissions known
    download: Optional[Callable[[Path], None]] = None  # writes content to a path


@dataclass
class SyncResult:
    """What one sync changed."""

    source: str
    downloaded: List[str] = field(default_factory=list)
    unchanged: int = 0
    deleted: List[str] = field(default_factory=list)
    skipped: Dict[str, str] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)

    def summary(self) -> Dict[str, object]:
        """JSON-friendly counts for logs and audit records."""
        return {
            "source": self.source,
            "downloaded": len(self.downloaded),
            "unchanged": self.unchanged,
            "deleted": len(self.deleted),
            "skipped": len(self.skipped),
            "errors": len(self.errors),
        }


_UNSAFE = re.compile(r'[\x00-\x1f<>:"|?*\\]')


def safe_relpath(path: str) -> str:
    """Map a remote path to a safe mirror-relative path.

    Drops empty, `.` and `..` segments, replaces characters that are unsafe
    on common filesystems, and prefixes names starting with a dot (which
    ingestion would skip as hidden).

    Raises:
        ValueError: If nothing usable remains.
    """
    parts = []
    for part in PurePosixPath(path.replace("\\", "/")).parts:
        if part in ("/", "", ".", ".."):
            continue
        part = _UNSAFE.sub("_", part).strip().rstrip(".")
        if part.startswith("."):
            part = "_" + part.lstrip(".")
        if part:
            parts.append(_truncate(part))
    if not parts:
        raise ValueError(f"unusable remote path: {path!r}")
    return "/".join(parts)


def _truncate(name: str, limit: int = 200) -> str:
    """Fit a name in `limit` UTF-8 bytes, keeping its extension."""
    if len(name.encode()) <= limit:
        return name
    stem, dot, suffix = name.rpartition(".")
    if not dot or len(suffix) > 10:
        stem, suffix = name, ""
    else:
        suffix = "." + suffix
    budget = limit - len(suffix.encode())
    return stem.encode()[:budget].decode(errors="ignore").rstrip() + suffix


def fold(rel: str) -> str:
    """The name as case-insensitive, normalizing filesystems (APFS, NTFS, SMB) see it."""
    return unicodedata.normalize("NFC", rel).casefold()


def _error(e: Exception) -> str:
    """Error text without URL query strings (pre-authenticated download links carry tokens)."""
    if isinstance(e, httpx.HTTPStatusError):
        return f"HTTPStatusError: HTTP {e.response.status_code}"
    return re.sub(r"\?[^\s'\"]*", "?…", f"{type(e).__name__}: {e}")


def _unique(rel: str, key: str, taken: set) -> str:
    """Disambiguate duplicate names (Drive allows them, also by case) with the item key."""
    if fold(rel) not in taken:
        return rel
    p = PurePosixPath(rel)
    return str(
        p.with_name(f"{p.stem} ({re.sub(r'[^A-Za-z0-9]', '', key)[:8]}){p.suffix}")
    )


def sync(source: str, mirror: Path, items: Iterable[RemoteItem]) -> SyncResult:
    """Make `mirror` match the source's supported files, content and permissions."""
    mirror.mkdir(parents=True, exist_ok=True)
    state_path = mirror / STATE_FILE
    old = (
        json.loads(state_path.read_text(encoding="utf-8"))
        if state_path.is_file()
        else {}
    )
    result = SyncResult(source=source)
    new_state: Dict[str, Dict[str, str]] = {}
    access: Dict[str, List[str]] = {}
    taken: set = set()
    listed = 0

    for item in items:
        listed += 1
        try:
            rel = _unique(safe_relpath(item.path), item.key, taken)
        except ValueError as e:
            result.skipped[item.path] = str(e)
            continue
        if Path(rel).suffix.lower() not in SUPPORTED_SUFFIXES:
            result.skipped[rel] = "unsupported file type"
            continue
        if item.size is not None and item.size > MAX_FILE_BYTES:
            result.skipped[rel] = f"larger than {MAX_FILE_BYTES // 1024 // 1024} MB"
            continue
        taken.add(fold(rel))
        target = mirror / rel
        previous = old.get(item.key)
        if (
            previous
            and previous.get("version") == item.version
            and previous.get("path") == rel
            and target.is_file()
        ):
            result.unchanged += 1
        else:
            try:
                _download(item, target)
            except Exception as e:  # noqa: BLE001 - one bad item must not stop the sync
                result.errors[rel] = _error(e)
                if previous and previous.get("path") == rel and target.is_file():
                    new_state[item.key] = previous  # keep the last good copy
                    if item.principals is not None:
                        access[rel] = item.principals
                continue
            result.downloaded.append(rel)
        new_state[item.key] = {"path": rel, "version": item.version}
        if item.principals is not None:
            access[rel] = item.principals

    if old and not listed:
        # An unmounted share or unshared folder lists as empty: keep the mirror.
        result.errors["<listing>"] = (
            "the source listed no files; kept the previous mirror "
            f"(delete {mirror} to empty it on purpose)"
        )
        return result
    keep = {fold(entry["path"]): entry["path"] for entry in new_state.values()}
    for entry in old.values():
        old_path = mirror / entry["path"]
        kept = keep.get(fold(entry["path"]))
        if kept == entry["path"] or not old_path.is_file():
            continue
        # A case-only rename on a case-insensitive disk: the old name is the new file.
        if (
            kept
            and (mirror / kept).exists()
            and os.path.samefile(mirror / kept, old_path)
        ):
            continue
        old_path.unlink()
        result.deleted.append(entry["path"])
    _prune_empty_dirs(mirror)
    _write_json(state_path, new_state)
    _write_json(mirror / ACCESS_FILE, access)
    return result


def _download(item: RemoteItem, target: Path) -> None:
    if item.download is None:
        raise ValueError("item has no download")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".okf-part-")
    os.close(fd)
    try:
        item.download(Path(tmp))
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(tmp, path)


def _prune_empty_dirs(root: Path) -> None:
    for directory in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        if directory.name != ".okf" and not any(directory.iterdir()):
            directory.rmdir()


def iso_now() -> str:
    """Current UTC time for records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
