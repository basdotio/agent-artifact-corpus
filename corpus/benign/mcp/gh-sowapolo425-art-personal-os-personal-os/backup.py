"""Portable checked backups; restores never overwrite the active vault."""
import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from .store import Store, now

MAX_ARCHIVE = 32 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_FILES = 5000
MANIFEST = "personal-os-backup.json"


def checked_archive_names(names):
    canonical = set()
    for name in names:
        parts = PurePosixPath(name).parts
        if any(p.endswith((".", " ")) or any(ord(c) < 32 or c in '<>:"\\|?*' for c in p)
               or p.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}
               for p in parts):
            raise ValueError("Nonportable backup path")
        key = name.casefold()
        if key in canonical:
            raise ValueError("Case-insensitive backup path collision")
        canonical.add(key)


def create_backup(store):
    memory = io.BytesIO()
    manifest = {"format": "personal-os-backup", "version": 1, "created_at": now(), "files": []}
    total = 0
    with store.locked(), zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
        for directory, subdirs, names in os.walk(store.root, followlinks=False):
            subdirs[:] = [d for d in subdirs if d not in (".git", ".venv", "__pycache__")]
            for d in subdirs:
                store._safe(Path(directory) / d)
            for name in sorted(names):
                path = store._safe(Path(directory) / name)
                relative = path.relative_to(store.root).as_posix()
                if relative in (".personal-os/lock", MANIFEST):
                    continue
                if total + path.stat().st_size > MAX_TOTAL:
                    raise ValueError("Vault exceeds 128 MB backup limit")
                data = path.read_bytes()
                total += len(data)
                if total > MAX_TOTAL or len(manifest["files"]) >= MAX_FILES:
                    raise ValueError("Vault exceeds backup limits (128 MB / 5000 files)")
                manifest["files"].append({"path": relative, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
                archive.writestr(relative, data)
        checked_archive_names([i["path"] for i in manifest["files"]])
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        if len(manifest_bytes) > 1024 * 1024:
            raise ValueError("Backup manifest exceeds 1 MB; reduce the file count or path lengths")
        archive.writestr(MANIFEST, manifest_bytes)
        store._audit("backup", None)
    result = memory.getvalue()
    if len(result) > MAX_ARCHIVE:
        raise ValueError("Compressed backup exceeds 32 MB")
    return result


def restore_backup(store, data):
    if not isinstance(data, bytes) or len(data) > MAX_ARCHIVE:
        raise ValueError("Backup exceeds 32 MB")
    checked = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES + 1 or sum(i.file_size for i in infos) > MAX_TOTAL + 1024 * 1024:
            raise ValueError("Expanded backup exceeds limits")
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or MANIFEST not in names:
            raise ValueError("Duplicate paths or missing backup manifest")
        for info in infos:
            path = PurePosixPath(info.filename)
            if (info.orig_filename != info.filename or path.is_absolute() or path.as_posix() != info.filename or "\\" in info.orig_filename or any(p in (".", "..") or ":" in p for p in path.parts)
                or not path.parts or info.is_dir() or stat.S_ISLNK(info.external_attr >> 16)):
                raise ValueError("Unsafe backup path or symbolic link")
        checked_archive_names(names)
        if archive.getinfo(MANIFEST).file_size > 1024 * 1024:
            raise ValueError("Backup manifest exceeds limit")
        manifest = json.loads(archive.read(MANIFEST))
        if not isinstance(manifest, dict) or manifest.get("format") != "personal-os-backup" or manifest.get("version") != 1:
            raise ValueError("Unsupported backup format")
        entries = manifest.get("files")
        if not isinstance(entries, list) or len(entries) > MAX_FILES or any(not isinstance(i, dict) or not isinstance(i.get("path"), str) or type(i.get("size")) is not int or i["size"] < 0 or not isinstance(i.get("sha256"), str) for i in entries):
            raise ValueError("Invalid backup manifest")
        declared = [item["path"] for item in entries]
        if len(declared) != len(set(declared)) or set(declared) != set(names) - {MANIFEST}:
            raise ValueError("Manifest file list mismatch")
        for item in entries:
            content = archive.read(item["path"])
            if len(content) != item["size"] or hashlib.sha256(content).hexdigest() != item["sha256"]:
                raise ValueError("Backup integrity check failed")
            checked[item["path"]] = content
    parent = store.root.parent
    staging = Path(tempfile.mkdtemp(prefix=".personal-os-restore-", dir=parent))
    target = parent / (store.root.name + "-restored-" + uuid.uuid4().hex[:10])
    try:
        restored = Store(staging)
        for name, content in checked.items():
            path = restored._safe(staging / name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        restored.init()
        os.rename(staging, target)
    except BaseException:
        if staging.exists() and staging.resolve().parent == parent and staging.name.startswith(".personal-os-restore-"):
            shutil.rmtree(staging)
        raise
    with store.locked():
        store._audit("restore_backup", None)
    return {"restored_vault": str(target), "files": len(checked), "active_vault_unchanged": True}
