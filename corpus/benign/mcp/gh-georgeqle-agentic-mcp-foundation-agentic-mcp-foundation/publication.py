"""Recoverable publication of small control files and plugin directories.

Callers hold their install lock. Large immutable payloads are staged separately.
"""

import json
import os
import shutil
import uuid
from pathlib import Path

from .transport import atomic_json


def atomic_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex)
    try:
        with temporary.open("xb") as output:
            os.chmod(temporary, 0o600)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def target(home, name):
    path = (home / name).resolve()
    if not path.is_relative_to(home.resolve()):
        raise ValueError("Publication target escapes installation home")
    return path


def recover(home):
    transaction = home / "publication"
    journal = transaction / "journal.json"
    if not transaction.exists():
        return
    if not journal.exists():
        # Publication does not start until the complete backup journal is durable.
        shutil.rmtree(transaction)
        return
    state = json.loads(journal.read_text())
    for index, entry in enumerate(state["entries"]):
        path = target(home, entry["name"])
        backup = transaction / str(index)
        if entry["directory"]:
            if path.exists():
                shutil.rmtree(path)
            if entry["existed"]:
                shutil.copytree(backup, path)
        elif entry["existed"]:
            atomic_bytes(path, backup.read_bytes())
        else:
            path.unlink(missing_ok=True)
    shutil.rmtree(transaction)


def publish(home: Path, files: dict, directories: dict | None = None, verify=None):
    """On a caught failure restore the previous publication; retain backups if recovery fails."""
    recover(home)
    transaction = home / "publication"
    transaction.mkdir(mode=0o700)
    directories = directories or {}
    entries = []
    for name in [*files, *directories]:
        path = target(home, name)
        directory = name in directories
        entry = {"name": name, "directory": directory, "existed": path.exists()}
        backup = transaction / str(len(entries))
        if path.exists():
            if directory:
                shutil.copytree(path, backup)
            else:
                backup.write_bytes(path.read_bytes())
        entries.append(entry)
    atomic_json(transaction / "journal.json", {"entries": entries})
    try:
        for name, data in files.items():
            atomic_bytes(target(home, name), data)
        for name, source in directories.items():
            path = target(home, name)
            if path.exists():
                shutil.rmtree(path)
            shutil.copytree(source, path)
        if verify is not None:
            verify()
    except Exception:
        recover(home)
        raise
    shutil.rmtree(transaction)
