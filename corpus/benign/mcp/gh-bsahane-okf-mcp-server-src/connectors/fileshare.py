"""File share connector: a local or mounted folder (NFS, SMB, AFP).

Permissions come from the files themselves (`permissions: posix`): a file
readable by its group grants `group:<group name>`, a world-readable file
grants `*`, and the owner is always granted `user:<owner name>`. Mount
options decide which owner and group the server sees, so check them on the
ingest host. Use `permissions: none` to leave access to `_okf.yaml` rules.
"""

import grp
import hashlib
import os
import pwd
import shutil
import stat
from functools import partial
from pathlib import Path
from typing import Iterator, List, Optional

from okf_mcp_server.src.connectors.base import RemoteItem


def _name(lookup, ident: int) -> str:
    try:
        return lookup(ident)[0]
    except KeyError:
        return str(ident)


def posix_principals(st) -> List[str]:
    """Principals from a file's owner, group and mode bits."""
    principals = [f"user:{_name(pwd.getpwuid, st.st_uid)}"]
    if st.st_mode & stat.S_IRGRP:
        principals.append(f"group:{_name(grp.getgrgid, st.st_gid)}")
    if st.st_mode & stat.S_IROTH:
        principals.append("*")
    return principals


def _copy(src: Path, target: Path) -> None:
    shutil.copy2(src, target)


def _walk(root: Path) -> Iterator[Path]:
    """Files under `root`, following links (to files or folders) that stay inside it.

    Kubernetes mounts ConfigMaps and Secrets as links into a hidden `..data`
    folder, including links to folders when items have sub-paths. Hidden
    names are skipped; real paths are tracked so link loops end.
    """
    seen = set()
    for current, dirs, files in os.walk(root, followlinks=True):
        real = os.path.realpath(current)
        if real in seen or not Path(real).is_relative_to(root):
            dirs[:] = []
            continue
        seen.add(real)
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            path = Path(current) / name
            if name.startswith(".") or not path.is_file():
                continue
            if not path.resolve().is_relative_to(root):
                continue
            yield path


def list_items(root: Path, permissions: str = "posix") -> Iterator[RemoteItem]:
    """Every regular file under `root`; symlinks only if they resolve inside it."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"file share not found or not a directory: {root}")
    for path in _walk(root):
        rel = path.relative_to(root).as_posix()
        st = path.stat()
        principals: Optional[List[str]] = (
            posix_principals(st) if permissions == "posix" else None
        )
        version = hashlib.sha256(f"{st.st_mtime_ns}:{st.st_size}".encode()).hexdigest()[
            :16
        ]
        yield RemoteItem(
            key=rel,
            path=rel,
            version=version,
            size=st.st_size,
            principals=principals,
            download=partial(_copy, path),
        )
