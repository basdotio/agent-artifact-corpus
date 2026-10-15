"""Ledger JSONL, feedback backups, HTML snapshots (PLAN.md §14)."""

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

from .config import Settings, private_dir
from .schemas import ScanFeedback, ToolError


def data_subdir(settings: Settings, name: str) -> Path:
    """DATA_DIR/<name>, both 0700: mkdir(parents=True) alone would leave DATA_DIR at umask perms (§6.4)."""
    private_dir(settings.data_dir)
    return private_dir(settings.data_dir / name)


SNAPSHOT_RETENTION_DAYS = 30  # §14: snapshots hold full page HTML (PII)


def purge_old_snapshots(settings: Settings) -> int:
    """Delete snapshots older than 30 days (§14 retention). Returns how many were removed; never raises."""
    cutoff = time.time() - SNAPSHOT_RETENTION_DAYS * 86400
    removed = 0
    for path in (settings.data_dir / "snapshots").glob("*.html"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            pass  # a stale snapshot must never break the tool that is saving a new one
    return removed


def save_snapshot(settings: Settings, name: str, html: str) -> Path:
    """Write page HTML to snapshots/<name>-<timestamp>-<random>.html.

    mkstemp creates the file exclusively with 0600 (contains PII, §6.4) and a unique suffix,
    so same-second snapshots never overwrite each other.
    """
    try:
        snap_dir = data_subdir(settings, "snapshots")
        fd, path = tempfile.mkstemp(prefix=f"{name}-{datetime.now():%Y%m%dT%H%M%S}-", suffix=".html", dir=snap_dir)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
    except OSError as e:  # every snapshot (success and site_changed paths) goes through here
        raise ToolError("storage_error", f"Cannot write HTML snapshot ({type(e).__name__}).",
                        "Stop. Fix DATA_DIR permissions/space, then retry.") from e
    purge_old_snapshots(settings)
    return Path(path)


def ledger_key(entry: dict) -> str:
    """scan_id, or "attempt:<id>" for a submitted scan whose id was not captured yet (§10.2)."""
    return str(entry["scan_id"]) if entry.get("scan_id") is not None else f"attempt:{entry['attempt_id']}"


def load_ledger(settings: Settings) -> dict[str, dict]:
    """Read ledger.jsonl into {ledger_key: entry}. Append-only: a later line for the same key wins (§14)."""
    path = settings.data_dir / "ledger.jsonl"
    entries: dict[str, dict] = {}
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    entries[ledger_key(entry)] = entry
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise ToolError(
            "storage_error", f"Cannot read ledger.jsonl in DATA_DIR ({type(e).__name__}).",
            "Inspect or repair ledger.jsonl; do not delete scans until it reads cleanly.",
        ) from e
    return entries


def append_ledger(settings: Settings, entry: dict) -> None:
    """Append one full entry (0600 file, O_APPEND, fsync'd): the ledger is the only record of MCP-created scans."""
    try:
        private_dir(settings.data_dir)
        fd = os.open(settings.data_dir / "ledger.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        os.fchmod(fd, 0o600)  # the open() mode only applies on creation; fix a pre-existing permissive file
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except OSError as e:
        raise ToolError("storage_error", f"Cannot write ledger.jsonl ({type(e).__name__}).",
                        "Stop. Fix DATA_DIR permissions/space before any further scan operation.") from e


def update_ledger(settings: Settings, key: str, **fields) -> dict:
    """Append `key`'s entry merged with `fields` (append-only update; the later line wins)."""
    entry = {**load_ledger(settings).get(key, {}), **fields}
    append_ledger(settings, entry)
    return entry


def feedback_backup(settings: Settings, scan_id: str) -> Path | None:
    """Existing backup path if it re-validates as ScanFeedback *for this scan_id* (§14 re-verify before delete)."""
    path = settings.data_dir / "feedback" / f"{scan_id}.json"
    try:
        backup = ScanFeedback.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return path if backup.scan_id == scan_id else None


def backup_feedback(settings: Settings, feedback: ScanFeedback) -> Path:
    """Write feedback/<scan_id>.json (0600) atomically: temp file + os.replace, so a crash never leaves a
    truncated backup that delete_scan could later trust (§14)."""
    try:
        backup_dir = data_subdir(settings, "feedback")
        fd, tmp = tempfile.mkstemp(prefix=f".{feedback.scan_id}-", suffix=".json", dir=backup_dir)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(feedback.model_dump_json(indent=2))
        path = backup_dir / f"{feedback.scan_id}.json"
        os.replace(tmp, path)
    except OSError as e:
        raise ToolError("storage_error", f"Cannot write feedback backup ({type(e).__name__}).",
                        "Stop. Fix DATA_DIR permissions/space; never delete a scan without a backup.") from e
    return path
