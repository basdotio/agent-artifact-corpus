"""Out-of-band file transfer between the user's machine and the cloud
(experiment branch).

Why this exists: an MCP tool result is fed to the model verbatim, so the
bytes of a transferred file — binary or large ones in particular — must not
travel inside one. Here the MCP tool only *starts* a transfer and reports
where the file ended up; the bytes move over plain HTTP between the bridge
and this adapter. (Text files are different: `read_file` returns them to the
model line-bounded and capped, by design.)

    upload   (local -> cloud)   bridge PUTs fixed-size chunks, each one is
                                acknowledged; a dropped connection resumes
                                from the last acknowledged offset.
    download (cloud -> local)   bridge GETs with a Range header and resumes
                                the same way.

Both directions are verified with SHA-256 before the file is put in place
(written to a temporary name first, then renamed), so a half-transferred
file is never visible under its real name.

Landing layout (Octop per-user folder model): every user has exactly one
folder on the cloud machine, {LOCALOCTOP_USERS_DIR}/<user_id>/, and that
user's agent sees that folder as "/". The user_id of the token IS the folder
name, verbatim (Chinese names included). Uploads land at

    {LOCALOCTOP_USERS_DIR}/<user_id>/{LOCALOCTOP_LANDING_SUBDIR}/<rel>

and the agent sees them as "/{LOCALOCTOP_LANDING_SUBDIR}/<rel>". Downloads
can only read paths inside the user's own folder — the folder of the token
owner, nobody else's. The user folder must already exist (it belongs to the
Octop platform); this module never creates it.

Threat model (why every path operation goes through a dir_fd): the user's
own AI can create, delete, rename and symlink anything inside its folder at
any moment, including between our checks and our writes. A path we verified
a millisecond ago can point somewhere else now. So every path operation this
module performs inside a user folder is anchored to directory handles that
were opened without following links (os.open with O_DIRECTORY | O_NOFOLLOW,
one component at a time from the user root), and every create / read /
rename / unlink happens relative to such a handle (dir_fd=…). Once we hold
the handle of the landing directory, swapping names around it cannot move
our reads or writes anywhere else.

Upload temp files are anonymous (O_TMPFILE): they have no name at all, so
nothing the user does to their folder can touch them. On completion the fd
is given its final name directly (a /proc/self/fd linkat relative to the
verified landing directory handle), so the process never leaves a visible
intermediate name behind. A name that is already taken is moved aside first
— atomically and never by overwriting (renameat2 with RENAME_NOREPLACE) —
so cloud-side work under the landing name is never destroyed.
"""

from __future__ import annotations

import asyncio
import ctypes
import errno
import fcntl
import hashlib
import json
import logging
import os
import re
import secrets
import shutil
import stat as statmod
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.requests import ClientDisconnect

from .errors import (
    BridgeProtocolError,
    CODE_INTERNAL,
    CODE_INVALID_PARAMS,
    CODE_METHOD_NOT_FOUND,
    CODE_NO_BRIDGE,
    CODE_NOT_ALLOWED,
    CODE_NOT_FOUND,
    CODE_TIMEOUT,
    CODE_TOO_LARGE,
)
from .tokens import KIND_BRIDGE

logger = logging.getLogger("localoctop.transfers")

CHUNK_BYTES = 4 * 1024 * 1024
MAX_CHUNK_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_TRANSFER_BYTES = 1024 * 1024 * 1024  # 1024 MiB
# Keep this much disk free after a transfer lands, so one big file cannot
# fill the volume the rest of the platform lives on.
DISK_RESERVE_BYTES = 1024 * 1024 * 1024
# A transfer with no byte movement for this long is declared dead (the
# machine went offline / the bridge was closed).
STALL_SECONDS = float(os.environ.get("LOCALOCTOP_TRANSFER_STALL_SECONDS", 420))
# How often the background task scans for stalled transfers and expired
# records. The scan also runs on transfer_status polls; this task is what
# releases the handles of a transfer nobody ever asks about again.
SCAN_INTERVAL_SECONDS = float(os.environ.get("LOCALOCTOP_TRANSFER_SCAN_INTERVAL", 30))
# Finished transfer records are kept this long for transfer_status lookups.
RECORD_TTL_SECONDS = 3600.0
# How long aclose() waits for a transfer's in-flight completion flow (the
# lock-holding section of _complete/_put_chunk) before cancelling it. The
# whole landing path — hashing the moved-aside copy, renameat2, the ledger
# write — is local disk I/O and normally finishes in well under a second;
# 5 s is generous headroom for a slow disk without letting shutdown hang.
CLOSE_WAIT_SECONDS = 5.0

# A ledger larger than this is treated as "no ledger": the per-user ledger
# holds a handful of small entries, so megabytes of JSON cannot be one.
_LEDGER_MAX_BYTES = 16 * 1024 * 1024
# Format marker at the top level of every ledger file we write, so a later
# format version can recognise what it is reading.
_LEDGER_MARK = "_localoctop_ledger"

# A user name (== the token's user_id == the Octop folder name) must not
# contain anything that could break the one-folder-per-user confinement.
# Includes C0, DEL and the C1 block (U+0080-U+009F).
_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f]")

_O_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _human(n: int) -> str:
    """A byte count the model can read at a glance."""
    f = float(n)
    for unit in ("bytes", "KiB", "MiB", "GiB", "TiB"):
        if f < 1024 or unit == "TiB":
            return f"{int(f):,} bytes" if unit == "bytes" else f"{f:.1f} {unit} ({n:,} bytes)"
        f /= 1024
    return f"{n:,} bytes"


def _plain(exc: BaseException) -> str:
    """A short plain-language reason from an exception, never a traceback."""
    msg = getattr(exc, "message", None) or str(exc) or exc.__class__.__name__
    return str(msg)[:300]


def _all_done(b: dict[str, Any]) -> bool:
    return b["done"] + b["fresh"] + len(b["failed"]) >= b["total"]


def _is_directory_refusal(exc: BridgeProtocolError) -> bool:
    """Whether a bridge error is the pre-whole-folder refusal of a directory.
    Older bridges answer a directory with CODE_INVALID_PARAMS and the wording
    "path is a directory; send files one at a time"; that is how a new adapter
    recognises an old client and answers the normal update-program text
    instead of relaying a program error."""
    return exc.code == CODE_INVALID_PARAMS and "director" in exc.message.lower()


def _open_dir(parent_fd: int, name: str) -> int:
    """Open one directory component relative to a parent handle without
    following links. A symlink (or anything that is not a directory) raises
    NotADirectoryError; a missing name raises FileNotFoundError."""
    return os.open(name, _O_DIR_FLAGS, dir_fd=parent_fd)


def _check_user_name(user_id: str) -> str:
    """Validate that user_id is safe to use as a folder name, verbatim.

    Allowed: any non-blank name without path separators or control
    characters — Chinese names such as '马威' are fine and kept as-is, and
    a leading dot is fine too (matches the upstream Octop rule; a user
    folder named ".hidden" is still confined to its own tree). Control
    characters include C0, DEL and the C1 block (U+0080-U+009F).
    """
    if not user_id or not user_id.strip():
        raise BridgeProtocolError(
            CODE_INVALID_PARAMS,
            "the token's user name is empty or all whitespace; it cannot be used "
            "as a folder name on the cloud machine")
    if user_id in (".", ".."):
        raise BridgeProtocolError(
            CODE_INVALID_PARAMS,
            f"the token's user name {user_id!r} is not a valid folder name "
            "(it would escape the per-user folder)")
    if "/" in user_id or "\\" in user_id:
        raise BridgeProtocolError(
            CODE_INVALID_PARAMS,
            f"the token's user name {user_id!r} contains a path separator; "
            "a user name must be a single folder name")
    if _CTRL.search(user_id):
        raise BridgeProtocolError(
            CODE_INVALID_PARAMS,
            f"the token's user name {user_id!r} contains control characters; "
            "a user name must be plain text")
    return user_id


def _stat_name(dir_fd: int, name: str) -> os.stat_result | None:
    """lstat of one name relative to a dir handle; None when absent."""
    try:
        return os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except OSError:
        return None


class _NotAFolder(Exception):
    """A path component that must be a directory is a symlink or file."""

    def __init__(self, name: str):
        super().__init__(name)
        self.name = name

    def refuse(self) -> BridgeProtocolError:
        # A symlink (or a file) sits where a directory must be: following it
        # could land outside the user's folder.
        return BridgeProtocolError(
            CODE_NOT_ALLOWED,
            f"the landing path {self.name!r} is a link or not a folder; "
            "the transfer was not started (it could point outside "
            "your own folder). Remove it and try again.")


class _Dirs:
    """A chain of verified directory handles for one user.

    `_Dirs(root_fd, comps)` opens each component of comps below root_fd with
    O_NOFOLLOW; `enter(name, create=…)` descends one more verified component
    as a new chain that shares the parent's fds. Once a handle is open it
    keeps naming the directory it was opened on — nothing the user swaps in
    their folder afterwards can redirect our operations.
    """

    def __init__(self, root_fd: int, comps: list[str], create: bool = False):
        self._fds = [root_fd]
        self.path: list[str] = []
        try:
            self._open(comps, create)
        except BaseException:
            # Construction failed: close only the fds this chain opened
            # itself; root_fd stays with the caller, which owns it.
            for fd in self._fds[1:]:
                try:
                    os.close(fd)
                except OSError:
                    pass
            self._fds = []
            raise

    @classmethod
    def _child(cls, parent: _Dirs, name: str, create: bool) -> _Dirs:
        child = cls.__new__(cls)
        child._fds = list(parent._fds)
        child.path = parent.path + [name]
        try:
            child._open([name], create)
        except BaseException:
            # Only the fd this level added is ours to close; the shared
            # parent fds stay with the parent chain.
            for fd in child._fds[len(parent._fds):]:
                try:
                    os.close(fd)
                except OSError:
                    pass
            child._fds = []
            raise
        return child

    def _open(self, names: list[str], create: bool) -> None:
        for name in names:
            try:
                fd = _open_dir(self._fds[-1], name)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(name, 0o700, dir_fd=self._fds[-1])
                fd = _open_dir(self._fds[-1], name)
            except NotADirectoryError:
                raise _NotAFolder(name) from None
            self._fds.append(fd)
            self.path.append(name)

    def enter(self, name: str, create: bool = False) -> _Dirs:
        """A chain one directory deeper (shares the parent's fds; close only
        the deepest chain you keep)."""
        return _Dirs._child(self, name, create)

    @property
    def fd(self) -> int:
        return self._fds[-1]

    def close(self) -> None:
        for fd in self._fds:
            try:
                os.close(fd)
            except OSError:
                pass
        self._fds = []


_O_FILE_FLAGS = (os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
                 | getattr(os, "O_NONBLOCK", 0))


def _ledger_file_name(user_id: str) -> str:
    """The ledger's file name for one user: the user name percent-encoded
    (reversible, and the alphabet it produces — letters, digits and
    '%XX' escapes — is safe on every filesystem). A user name may be
    Chinese, contain spaces or '%' itself; it is NEVER used verbatim."""
    return urllib.parse.quote(user_id, safe="") + ".json"


def _open_regular_file(dir_fd: int, name: str) -> int:
    """Open `name` below a verified dir handle for reading, refusing
    anything that is not a regular file.

    O_NONBLOCK is what keeps a FIFO (named pipe) from hanging the whole
    adapter: open(2) on a FIFO otherwise blocks until a writer shows up,
    and this call runs on the event loop thread — one user's pipe would
    stall transfers for EVERY user. O_NOFOLLOW refuses symlinks. Right
    after the open, fstat must say S_ISREG or the fd is closed and the
    caller gets OSError. O_NONBLOCK is then cleared so later reads behave
    like plain blocking file reads (it never had an effect on regular
    files; clearing keeps behaviour uniform)."""
    fd = os.open(name, _O_FILE_FLAGS, dir_fd=dir_fd)
    try:
        st = os.fstat(fd)
        if not statmod.S_ISREG(st.st_mode):
            raise OSError(errno.EINVAL, f"not a regular file: {name!r}", name)
        fcntl.fcntl(fd, fcntl.F_SETFL,
                    fcntl.fcntl(fd, fcntl.F_GETFL) & ~os.O_NONBLOCK)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _sha256_fd(fd: int) -> str:
    """SHA-256 of an open file, read through the fd itself: the digest is of
    the exact object that was verified, whatever happens to its name."""
    h = hashlib.sha256()
    offset = 0
    while True:
        block = os.pread(fd, 1024 * 1024, offset)
        if not block:
            break
        h.update(block)
        offset += len(block)
    return h.hexdigest()


def _sha256_fd_own(fd: int) -> str:
    """_sha256_fd on a duplicated fd the worker thread owns end to end:
    closes it no matter how the hashing ends. The coroutine that handed the
    fd over keeps its own — a cancelled coroutine closing its half can
    never pull the rug from under the thread (a bare fd number would be
    recycled by the next transfer, and the thread could then read someone
    else's file through it)."""
    try:
        return _sha256_fd(fd)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


async def _run_owning_fd(fn: Any, fd: int, *args: Any) -> Any:
    """Run fn(fd, *args) on a worker thread; the fd is closed EXACTLY once,
    whether or not the thread function ever runs.

    The leak this guards against: the coroutine is cancelled while the work
    item still sits in the executor queue — fn never runs, so nothing would
    ever close the dup'd fd.

    Ownership is settled under a lock so the two sides can never both close
    (a double close can hit a *recycled* fd number belonging to another
    transfer) and never both skip. The runner claims the fd under the lock
    before touching it; the cancelling coroutine may only close when the
    claim has not happened yet — and it marks the fd as taken, so a runner
    that gets scheduled later returns without touching a closed fd. (The
    return value of Future.cancel() cannot be used for this: asyncio's
    wrapper reports cancellation even when the thread is already running.)
    """
    loop = asyncio.get_running_loop()
    guard = threading.Lock()
    taken = {"thread": False, "caller": False}

    def runner() -> Any:
        with guard:
            if taken["caller"]:
                return None  # the cancelled coroutine already closed the fd
            taken["thread"] = True
        return fn(fd, *args)

    fut = loop.run_in_executor(None, runner)
    try:
        return await fut
    except asyncio.CancelledError:
        with guard:
            if not taken["thread"]:
                taken["caller"] = True
                try:
                    os.close(fd)
                except OSError:
                    pass
        raise


# ---------------------------------------------------------------- renameat2
# The Python standard library has no renameat2, so call libc directly.
# RENAME_NOREPLACE makes the rename fail with EEXIST when the destination
# name is taken — the only rename that can never overwrite someone's work.
_RENAME_NOREPLACE = 1

try:
    _libc = ctypes.CDLL("libc.so.6", use_errno=True)
    _libc.renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p,
                                ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    _libc.renameat2.restype = ctypes.c_int
except (OSError, AttributeError):  # not glibc: the fallback path is used
    _libc = None


def _rename_noreplace(dir_fd: int, old: str, new: str) -> None:
    """Atomically rename `old` to `new` relative to `dir_fd`, failing with
    FileExistsError instead of overwriting when `new` is already taken.

    Falls back to link+unlink when the kernel or libc has no renameat2;
    the fallback leaves a sub-microsecond window between link and unlink
    during which the file sits under both names (a concurrent swap of the
    source name would make us rename whatever the name holds at link time —
    still never an overwrite of `new`)."""
    global _renameat2_fallbacks
    old_b, new_b = os.fsencode(old), os.fsencode(new)
    if _libc is not None:
        rc = _libc.renameat2(dir_fd, old_b, dir_fd, new_b, _RENAME_NOREPLACE)
        if rc == 0:
            return
        err = ctypes.get_errno()
        if err not in (errno.ENOSYS, errno.EINVAL):
            raise OSError(err, os.strerror(err), old)
        # renameat2 unsupported at runtime: use the fallback below.
    # Fallback: link(new) refuses EEXIST, so `new` is never overwritten;
    # unlink(old) then removes the source name.
    _renameat2_fallbacks += 1
    os.link(old, new_b, src_dir_fd=dir_fd, dst_dir_fd=dir_fd, follow_symlinks=False)
    os.unlink(old_b, dir_fd=dir_fd)


# Counts link+unlink fallbacks: the test suite asserts this stays 0 in the
# container (the primary renameat2 path is the one production relies on).
_renameat2_fallbacks = 0


async def _first_of(*tasks: "asyncio.Task") -> None:
    """Return as soon as any of the given tasks completes (FIRST_COMPLETED
    semantics), without cancelling the others — wait() owns them and
    cancels them in its own finally."""
    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)


@dataclass
class Transfer:
    id: str
    ticket: str
    user_id: str
    pair_id: str
    direction: str            # "up" (local->cloud) | "down" (cloud->local)
    local_path: str
    cloud_path: Path
    size: int = 0
    mtime_unix: int = 0
    received: int = 0         # up: bytes acknowledged; down: highest byte served
    inflight: int = 0         # up: bytes of the chunk currently arriving (not yet applied)
    sha: Any = None
    expected_sha: str = ""
    state: str = "active"     # active | done | failed
    error: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    created: float = field(default_factory=time.monotonic)
    updated: float = field(default_factory=time.monotonic)
    finished: float = 0.0
    done: asyncio.Event = field(default_factory=asyncio.Event)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    # The coroutine currently running the completion flow (_complete),
    # registered by the complete route so aclose() can cancel it when the
    # shutdown wait runs out. Always the task that holds (or is about to
    # hold) `lock`.
    completion_task: asyncio.Task | None = None
    dirs: _Dirs | None = None       # verified dir handles of the landing folder
    file_fd: int = -1               # up: anonymous temp fd; down: verified source fd
    # Set when the transfer was declared dead because no byte moved for
    # STALL_SECONDS — i.e. the machine went offline or the client was closed.
    # A folder fetch uses this to tell "this one file failed" apart from "the
    # whole machine is gone", and stops the batch in the second case.
    offline: bool = False

    # A folder fetch (fetch_to_cloud with a directory path) is ONE record
    # whose batch field carries the progress of the whole run; the per-file
    # transfers it drives are ordinary Transfer records going through the
    # ordinary landing path. None for a single-file transfer.
    batch: dict[str, Any] | None = None
    # The background task driving that folder fetch, so the stall sweep can
    # tell "the batch is alive and between two files" from "the whole run
    # died". Only ever set together with batch.
    batch_task: asyncio.Task | None = None

    def touch(self) -> None:
        self.updated = time.monotonic()

    def is_error(self) -> bool:
        """Whether the model should see this as an error. A limit advisory is
        a normal answer with a way forward, not a failure."""
        return self.state == "failed" and not self.result.get("advisory")

    def finish(self, ok: bool, error: str = "") -> None:
        if self.state != "active":
            return
        self.state = "done" if ok else "failed"
        self.error = error
        self.finished = time.monotonic()
        # Anonymous temp data dies with its fd; the temp name was never
        # visible at all, so there is nothing to sweep. Handles are never
        # left behind — this runs on success, failure, abort and timeout.
        if self.file_fd >= 0:
            try:
                os.close(self.file_fd)
            except OSError:
                pass
            self.file_fd = -1
        if self.dirs is not None:
            self.dirs.close()
            self.dirs = None
        self.done.set()


class TransferManager:
    def __init__(self, settings: Any, registry: Any, url_base: str):
        self.settings = settings
        self.registry = registry
        self.url_base = url_base.rstrip("/")
        e = os.environ
        # Mount point of all per-user Octop folders: {users_dir}/<user_id>/.
        self.users_dir = Path(e.get("LOCALOCTOP_USERS_DIR", "/users"))
        # Sub-folder inside each user's folder where fetched files land (the
        # agent sees it as "/{landing_subdir}"). Must be ONE plain directory
        # name: anything else (a path, ".", control characters) would break
        # the handle-anchored confinement below, so refuse to start at all.
        raw_subdir = e.get("LOCALOCTOP_LANDING_SUBDIR", "localoctop")
        if (not raw_subdir or raw_subdir in (".", "..")
                or "/" in raw_subdir or "\\" in raw_subdir
                or _CTRL.search(raw_subdir)):
            raise ValueError(
                f"LOCALOCTOP_LANDING_SUBDIR must be a single directory name "
                f"(no '/', '\\\\', '.'/'..' or control characters), got {raw_subdir!r}")
        self.landing_subdir = raw_subdir
        self.max_bytes = int(e.get("LOCALOCTOP_MAX_TRANSFER_BYTES", DEFAULT_MAX_TRANSFER_BYTES))
        # Service-owned state directory: the transfer ledger lives here
        # (one file per user), never inside the users' own folders. It is
        # created at startup with 0700; a directory we cannot create or
        # write to is a hard startup error — running without a writable
        # ledger home would silently degrade every transfer.
        raw_state = (getattr(settings, "state_dir", None)
                     or e.get("LOCALOCTOP_STATE_DIR") or "state")
        self.state_dir = Path(raw_state)
        self.ledger_dir = self.state_dir / "ledger"
        try:
            os.makedirs(self.state_dir, mode=0o700, exist_ok=True)
            os.chmod(self.state_dir, 0o700)
            os.makedirs(self.ledger_dir, mode=0o700, exist_ok=True)
            os.chmod(self.ledger_dir, 0o700)
        except OSError as exc:
            raise ValueError(
                f"LOCALOCTOP_STATE_DIR {raw_state!r} cannot be created or used "
                f"as the service state directory: {exc}") from exc
        if not self.ledger_dir.is_dir():
            raise ValueError(
                f"LOCALOCTOP_STATE_DIR {raw_state!r}: {str(self.ledger_dir)!r} "
                "exists but is not a directory")
        try:
            probe = self.ledger_dir / f".probe-{secrets.token_urlsafe(8)}"
            fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
            os.unlink(probe)
        except OSError as exc:
            raise ValueError(
                f"LOCALOCTOP_STATE_DIR {raw_state!r}: the ledger directory "
                f"{str(self.ledger_dir)!r} is not writable: {exc}") from exc
        self._transfers: dict[str, Transfer] = {}
        self._ledger_locks: dict[str, asyncio.Lock] = {}
        self._scan_task: asyncio.Task | None = None
        # The background tasks driving folder fetches. One entry per running
        # batch; aclose() cancels every one of them and waits for it to stop
        # touching its file's handles before finishing the batch record.
        self._batch_tasks: set[asyncio.Task] = set()
        # Set when the service enters its shutdown flow (aclose): every
        # in-progress tool call waiting on a transfer must wake up AT ONCE
        # and answer (with a "the service is restarting" line) instead of
        # being cut off mid-wait. Checked inside wait().
        self.shutdown_event: asyncio.Event = asyncio.Event()

    def _ledger_lock(self, user_id: str) -> asyncio.Lock:
        """One lock per user: the read-modify-write of that user's ledger
        must be serial (two transfers completing at once must not lose each
        other's records)."""
        lock = self._ledger_locks.get(user_id)
        if lock is None:
            lock = self._ledger_locks[user_id] = asyncio.Lock()
        return lock

    # ------------------------------------------------------------ helpers
    def _user_root_fd(self, user_id: str) -> int:
        """A dir handle to the user's Octop folder, opened without following
        links (a symlink where the folder should be is refused — following
        it would smuggle one user's traffic into another's folder).

        The folder must already exist (it belongs to the platform); we never
        create it: an account without a folder simply cannot transfer."""
        name = _check_user_name(user_id)
        try:
            top_fd = os.open(self.users_dir, _O_DIR_FLAGS)
        except OSError:
            raise BridgeProtocolError(
                CODE_NOT_FOUND,
                f"this account has no folder on the cloud machine yet "
                f"(no Octop user named {user_id!r}); the transfer was not started. "
                "Create the Octop user first, then try again.")
        try:
            return _open_dir(top_fd, name)
        except NotADirectoryError:
            raise BridgeProtocolError(
                CODE_NOT_ALLOWED,
                f"the folder for user {user_id!r} on the cloud machine is a link, "
                "not a real folder; refusing to transfer (platform misconfiguration)")
        except OSError:
            raise BridgeProtocolError(
                CODE_NOT_FOUND,
                f"this account has no folder on the cloud machine yet "
                f"(no Octop user named {user_id!r}); the transfer was not started. "
                "Create the Octop user first, then try again.")
        finally:
            os.close(top_fd)

    def _dest_for(self, user_id: str, rel: str, name: str) -> tuple[list[str], PurePosixPath]:
        """Cloud landing location for a local file (stable per local path).

        Returns (components below the user root, path the agent sees). No
        disk access happens here — components are opened through _Dirs when
        the transfer actually starts."""
        _check_user_name(user_id)
        rel = rel.replace("\\", "/")
        parts = [p for p in PurePosixPath(rel).parts if p not in ("", ".", "..", "/")]
        # An absolute local path (file outside every whitelist root should
        # never reach here, but be defensive): keep only the file name.
        if not parts or re.match(r"^[A-Za-z]:", parts[0]) or rel.startswith("/"):
            parts = [name or "file"]
        clean = [re.sub(r'[<>:"|?*\x00-\x1f]', "_", p) for p in parts]
        visible = PurePosixPath("/") / self.landing_subdir / PurePosixPath(*clean)
        return [self.landing_subdir, *clean], visible

    def _ledger_load(self, user_id: str) -> dict[str, Any]:
        """Read one user's ledger from the service state directory.

        Never raises into request handling: a missing, empty, oversized,
        non-UTF-8, non-JSON, wrongly-shaped or insanely nested file reads
        as "no records" (one warning is logged); a single entry that is
        not an object is skipped, so every caller downstream only ever
        sees well-typed values."""
        path = self.ledger_dir / _ledger_file_name(user_id)
        try:
            st = os.stat(path)
            if not statmod.S_ISREG(st.st_mode) or st.st_size > _LEDGER_MAX_BYTES:
                if st.st_size > _LEDGER_MAX_BYTES:
                    logger.warning("ledger for user %r is oversized (%d bytes); treated as empty",
                                   user_id, st.st_size)
                return {}
            raw = path.read_bytes()
        except FileNotFoundError:
            return {}
        except OSError as exc:
            logger.warning("could not read the ledger for user %r: %s", user_id, exc)
            return {}
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, RecursionError, MemoryError) as exc:
            logger.warning("ledger for user %r is not readable JSON (%s); treated as empty",
                           user_id, exc)
            return {}
        if not isinstance(data, dict):
            logger.warning("ledger for user %r is not a JSON object; treated as empty", user_id)
            return {}
        return {k: v for k, v in data.items()
                if k != _LEDGER_MARK and isinstance(v, dict)}

    def _ledger_save(self, user_id: str, entries: dict[str, Any]) -> None:
        """Replace one user's ledger atomically: the temp file is written
        in the SAME directory, fsynced, then os.replace'd onto the real
        name. The file is 0600 — it is the service's own book, nobody
        else's business."""
        path = self.ledger_dir / _ledger_file_name(user_id)
        data = json.dumps({**entries, _LEDGER_MARK: 1}, ensure_ascii=False).encode("utf-8")
        tmp = self.ledger_dir / f".tmp-{secrets.token_urlsafe(12)}"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        except BaseException:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        try:
            os.replace(tmp, path)
            os.chmod(path, 0o600)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _keep_cloud_edited(self, dirs: _Dirs, name: str) -> str:
        """Move `name` (a regular file at the landing position that is NOT
        the copy we landed last time — the agent edited it, or we have no
        record of it) aside to "<stem>.cloud-edited-<YYYYMMDD-HHMMSS><ext>"
        so a re-fetch never destroys cloud-side work.

        Everything happens relative to the verified dir handle and the move
        uses renameat2(RENAME_NOREPLACE): it either happens in one atomic
        step or fails with EEXIST — there is no check-then-act window for
        the agent to slip into, and nothing at the keep-as name is ever
        overwritten (a taken candidate gets a numeric suffix).
        FileNotFoundError propagates: the occupant was moved away by someone
        else first, and the caller retries the landing link. Returns the
        kept-as name."""
        stem, dot, ext = name.rpartition(".")
        if not dot:  # no extension, or a dotfile like ".env"
            stem, ext = name, ""
        else:
            ext = "." + ext
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        base = f"{stem}.cloud-edited-{stamp}"
        for i in range(0, 1000):
            cand = f"{base}{'' if i == 0 else f'-{i}'}{ext}"
            try:
                _rename_noreplace(dirs.fd, name, cand)
            except FileExistsError:
                continue
            logger.info("cloud copy of %s was modified; kept as %s", name, cand)
            return cand
        raise OSError(f"no free keep-as name for the modified cloud copy of {name!r}")

    def _gc(self) -> None:
        now = time.monotonic()
        for tid, t in list(self._transfers.items()):
            if t.state != "active" and now - t.finished > RECORD_TTL_SECONDS:
                self._transfers.pop(tid, None)

    async def _check_stall(self, t: Transfer) -> None:
        """Declare a transfer dead if no byte moved for STALL_SECONDS.

        The finish never races the completion flow: the flow
        (_complete/_put_chunk) runs entirely inside t.lock and is the only
        user of the transfer's dir handles in that window, so aborting
        while the lock is held would close t.dirs under a coroutine still
        using it. Held lock -> skipped; the next pass (or aclose's wait)
        retries.

        A folder-batch record is never aborted by the sweep while its
        driving task is alive: that task owns the record's lifecycle and
        touches it at least every couple of seconds (once per file it
        starts and once per poll of the file in flight), so a batch that
        still has a live task is making progress by construction. The
        per-file transfers it drives are swept by this same rule like any
        other transfer."""
        if t.state != "active":
            return
        if t.batch is not None:
            task = t.batch_task
            if task is not None and not task.done():
                return
        if time.monotonic() - t.updated <= STALL_SECONDS:
            return
        if t.lock.locked():
            return  # completion in flight: retry next sweep
        t.offline = True  # no byte moved for STALL_SECONDS: the machine is gone
        t.finish(False, "the transfer stopped making progress — the local machine went offline "
                        "or the localoctop client was closed. Start it again when the machine is back.")

    async def sweep_transfers(self) -> None:
        """One pass over every transfer record: stall-abort actives that
        stopped making progress (their handles are closed by finish()) and
        drop finished records past the retention TTL.

        A transfer whose lock is held (a completion flow using its dir
        handles) is skipped, never aborted mid-use — the scan itself never
        blocks on a transfer. This is called by the background scan task AND
        directly by tests — a transfer nobody ever asks about again must not
        hold its file and directory handles forever."""
        for t in list(self._transfers.values()):
            await self._check_stall(t)
        self._gc()

    def _ensure_scan_task(self) -> None:
        """Start the periodic sweep if it is not running yet. Lazy so the
        manager also works where no lifespan event ever fires (tests, and
        ASGI transports that skip startup)."""
        task = self._scan_task
        if task is not None and not task.done():
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return  # no event loop yet (sync context); retried on next _new
        self._scan_task = asyncio.create_task(self._scan_loop())

    async def _scan_loop(self) -> None:
        while True:
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)
            try:
                await self.sweep_transfers()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("transfer scan failed; retrying next interval")

    async def aclose(self) -> None:
        """Shut the manager down: stop the background scan, then fail every
        transfer still in flight and release its handles (called from the
        app lifespan on shutdown). fds handed to worker threads were
        duplicated first (the thread closes its own copy), so closing the
        coroutine's copies here cannot touch I/O still running.

        A completion flow in progress (holding the transfer's lock, using
        its dir handles) is never closed out from under it: it gets
        CLOSE_WAIT_SECONDS, then is cancelled, then the loop keeps waiting
        until it has actually exited the lock-holding section — a cancelled
        flow stops touching the handles before its lock exits. Shutdown may
        take a moment past the deadline when the worker-thread hashing of
        the moved-aside copy is still finishing; that is the price of never
        closing a handle while it can still be read."""
        # Wake every tool call waiting on a transfer RIGHT NOW, before any
        # other shutdown work: they must get their "the service is
        # restarting" answer out while uvicorn still lets in-flight requests
        # finish, not be cut off mid-wait.
        self.shutdown_event.set()
        task = self._scan_task
        self._scan_task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        # Folder fetches run as background tasks that drive ordinary per-file
        # transfers. Cancel them FIRST and wait for them to actually stop:
        # while one is alive it may be inside a file's start_upload, and only
        # once it has exited can the loop below be sure it is looking at every
        # handle still held. Each cancelled batch finishes its own record (its
        # finally block), so nothing is left 'active' for the model to poll.
        await self._stop_batch_tasks()
        for t in list(self._transfers.values()):
            if t.state != "active":
                continue
            try:
                # Acquiring the lock synchronises with the completion flow:
                # once held, finish() is the only thing still using t.dirs
                # and the flow has already exited the lock.
                await asyncio.wait_for(t.lock.acquire(), timeout=CLOSE_WAIT_SECONDS)
            except asyncio.TimeoutError:
                # The completion flow is stuck in an await (a slow hash
                # thread, typically): cancel it so the coroutine stops
                # touching the handles, then keep waiting for its exit.
                ct = t.completion_task
                if ct is not None and not ct.done():
                    ct.cancel()
                logger.warning("aclose: waiting for the completion flow of transfer %s "
                               "to exit after cancellation", t.id)
                try:
                    await asyncio.wait_for(t.lock.acquire(), timeout=CLOSE_WAIT_SECONDS)
                except asyncio.TimeoutError:
                    # Still not out (a thread it awaits holds it far longer
                    # than any sane shutdown window). The flow no longer
                    # holds the event loop, so closing here would NOT close
                    # a handle it can still use after resuming — but it
                    # would close one a STUCK flow may resume into, so skip
                    # the finish and let the process exit clean up instead.
                    logger.error("aclose: transfer %s completion flow still not out; "
                                 "skipping its finish (process exit reclaims the fd)",
                                 t.id)
                    continue
            try:
                t.finish(False, "the localoctop adapter is shutting down; start the transfer again")
            finally:
                t.lock.release()

    def _abort(self, t: Transfer, msg: str) -> None:
        t.finish(False, msg)

    def _fail_unexpected(self, t: Transfer, where: str, ref: str) -> None:
        """End a transfer as failed after an unexpected internal problem on
        the bridge-facing HTTP line: the record must not stay 'active' (the
        model would poll it forever), and the reason is plain language plus
        the reference id — never the raw exception."""
        t.finish(False, f"the localoctop service hit an internal problem while {where} "
                        f"(reference for the administrator: {ref}); start the transfer again")

    def _new(self, **kw: Any) -> Transfer:
        self._gc()
        t = Transfer(id=secrets.token_urlsafe(9), ticket=secrets.token_urlsafe(24), **kw)
        self._transfers[t.id] = t
        self._ensure_scan_task()
        return t

    def _advisory(self, user_id: str, pair_id: str, direction: str, local_path: str,
                  visible: str, size: int, message: str) -> Transfer:
        """A finished, not-transferred record for a call that hit a limit.
        Hitting a limit is a normal answer with a way forward, not a failure:
        tools.py renders it as isError=false (result['advisory'])."""
        t = self._new(user_id=user_id, pair_id=pair_id, direction=direction,
                      local_path=local_path, cloud_path=Path(visible or local_path), size=size)
        t.result = {"advisory": True, "visible": visible}
        t.finish(False, message)
        return t

    def _bridge_params(self, t: Transfer) -> dict[str, Any]:
        return {"transfer_id": t.id, "ticket": t.ticket,
                "url_path": f"{self.url_base}/{t.id}", "chunk_bytes": CHUNK_BYTES}

    async def _call(self, user_id: str, pair_id: str, method: str, params: dict[str, Any]) -> Any:
        if pair_id:
            return await self.registry.call_paired(user_id, pair_id, method, params,
                                                   timeout=self.settings.bridge_timeout)
        return await self.registry.call(user_id, method, params, timeout=self.settings.bridge_timeout)

    def _open_agent_file(self, user_id: str, raw: str) -> tuple[int, _Dirs, os.stat_result]:
        """Map an agent-visible absolute path ("/..." inside the user's
        folder) to an open file, confined to the user's own folder.

        Every directory component is opened relative to its parent handle
        with O_NOFOLLOW, and the file itself with O_NOFOLLOW: a symlink at
        any step — planted before or during this call — is refused, never
        followed. Returns (file fd, open dir chain, fstat of the file). The
        caller owns the fd and the chain; because both are held, later reads
        keep seeing this exact file no matter how the folder is rearranged.
        """
        if not raw or "\x00" in raw:
            raise BridgeProtocolError(CODE_INVALID_PARAMS, "cloud_path is required")
        pp = PurePosixPath(raw)
        if not pp.is_absolute():
            raise BridgeProtocolError(
                CODE_INVALID_PARAMS,
                f"cloud_path must be an absolute path the agent sees, starting with '/' "
                f"(your folder is the root), got {raw!r}")
        parts = [p for p in pp.parts if p not in ("/", "")]
        if not parts:
            raise BridgeProtocolError(CODE_NOT_FOUND, f"cloud file not found: {raw}")
        for p in parts:
            if p in (".", "..") or "/" in p or "\\" in p:
                raise BridgeProtocolError(
                    CODE_INVALID_PARAMS,
                    f"cloud_path {raw!r} must not contain '.' / '..' / stray separators; "
                    "give the plain absolute path as you see it inside your folder")
        root_fd = self._user_root_fd(user_id)
        chain = _Dirs(root_fd, [])
        try:
            for comp in parts[:-1]:
                try:
                    chain = chain.enter(comp)
                except FileNotFoundError:
                    raise BridgeProtocolError(CODE_NOT_FOUND, f"cloud file not found: {raw}")
                except _NotAFolder:
                    # A symlink sits where a directory must be — refused,
                    # never followed.
                    raise BridgeProtocolError(
                        CODE_NOT_ALLOWED,
                        f"{raw!r} points outside your own folder on the cloud machine "
                        "(a link sits in its path); only files inside your own folder "
                        "can be sent to the user's machine")
            try:
                fd = _open_regular_file(chain.fd, parts[-1])
            except FileNotFoundError:
                raise BridgeProtocolError(CODE_NOT_FOUND, f"cloud file not found: {raw}")
            except OSError as exc:
                # ELOOP: the final component is a symlink. Anything else
                # (a directory, a FIFO, a device node — see
                # _open_regular_file) is not a regular file either: refused
                # without ever blocking on it.
                if exc.errno == errno.ELOOP:
                    raise BridgeProtocolError(
                        CODE_NOT_ALLOWED,
                        f"{raw!r} is a link, not a regular file; only files inside your own "
                        "folder can be sent to the user's machine")
                raise BridgeProtocolError(
                    CODE_NOT_FOUND,
                    f"{raw!r} is not a regular file (a directory, pipe or device cannot be "
                    "sent to the user's machine)")
            try:
                st = os.fstat(fd)
            except BaseException:
                os.close(fd)
                raise
            return fd, chain, st
        except BaseException:
            chain.close()
            raise

    async def _hash_matches(self, dirs: _Dirs, name: str, sha256: Any) -> bool:
        """True when the regular file `name` below the verified dir handle
        provably still is the recorded copy: it hashes (on its open fd,
        links never followed, FIFOs refused) to `sha256`, AND fstat before
        and after the hashing shows the same size, st_mtime_ns and
        st_ctime_ns — a file rewritten while we read it can coincidentally
        hash right only if nothing changed, so any change means "cannot
        prove untouched". That check does NOT close the race (a write can
        land between the second fstat and the caller's next step; it only
        catches the obvious cases); whenever in doubt the caller keeps the
        file. Any open or read failure — including a symlink or a mid-check
        deletion — simply means "not the same copy": the caller
        re-transfers."""
        if not isinstance(sha256, str) or not sha256:
            return False
        try:
            fd = _open_regular_file(dirs.fd, name)
        except OSError:
            return False
        try:
            st1 = os.fstat(fd)
            try:
                dup = os.dup(fd)
            except OSError:
                return False
            digest = await _run_owning_fd(_sha256_fd_own, dup)
            st2 = os.fstat(fd)
            if (st1.st_size, st1.st_mtime_ns, st1.st_ctime_ns) != \
                    (st2.st_size, st2.st_mtime_ns, st2.st_ctime_ns):
                return False  # changed while we hashed: cannot prove untouched
            return digest == sha256
        except OSError:
            return False
        finally:
            os.close(fd)

    # ------------------------------------------------------- start: upload
    async def start_upload(self, user_id: str, pair_id: str, local_path: str,
                           force: bool = False) -> Transfer:
        # 1) Open the user's folder first: no folder, no transfer (and
        #    nothing is created on disk for unknown accounts).
        root_fd = self._user_root_fd(user_id)
        try:
            # 2) Ask the machine what the file looks like right now. No
            #    max_bytes here: the real bridge refuses an over-limit file
            #    with a 4003 error before reporting its size, and deciding
            #    what an over-limit answer looks like is OUR job (a normal
            #    advisory below, not an error).
            try:
                info = await self._call(user_id, pair_id, "transfer_upload",
                                        {"path": local_path, "stat_only": True})
            except BridgeProtocolError as exc:
                # An OLDER bridge answers a directory probe with its old
                # "send files one at a time" refusal instead of is_dir. That
                # is the one case where a folder fetch means "your program is
                # old": answer a normal explanation, never the raw refusal.
                if _is_directory_refusal(exc):
                    return self._folder_advisory(
                        user_id, pair_id, local_path, str(local_path),
                        "this path is a folder, and the localoctop program on the user's computer "
                        "is an older version that cannot fetch a whole folder in one call. "
                        "Nothing was sent.\n"
                        "Next step: ask the user to update the localoctop program on their "
                        "computer, or fetch the individual files with fetch_to_cloud instead.",
                        tail=False)
                raise
            # The path is a FOLDER: fetch it whole. A current bridge marks it
            # on the stat probe, so detecting it costs no extra round trip.
            if info.get("is_dir"):
                return await self.start_upload_dir(user_id, pair_id, local_path, force=force)
            size, mtime = int(info.get("size", 0)), int(info.get("mtime_unix", 0))
            rel = str(info.get("path") or local_path)
            comps, visible = self._dest_for(user_id, rel, str(info.get("name") or ""))

            # 2b) Over the transfer limit? A normal answer with the way
            #     forward, not an error — and the machine is never asked to
            #     send a single byte.
            if size > self.max_bytes:
                return self._advisory(
                    user_id, pair_id, "up", rel, str(visible), size,
                    f"file is {size:,} bytes, over the {self.max_bytes:,}-byte transfer limit")

            # 3) Already have exactly this version in the cloud? Then do
            #    nothing — but only if the cloud file is still the very copy
            #    we landed: size and mtime must match the ledger record AND
            #    the file's current content must hash to the recorded
            #    sha256. Content is checked because an edit that keeps the
            #    size and restores the mtime (many copy/extract tools
            #    preserve times) would otherwise look "unchanged". The file
            #    is opened relative to the verified dir handle without
            #    following links, and the hash is computed on the open fd in
            #    a worker thread (never blocking the event loop, never
            #    re-resolving the name).
            key = f"{pair_id}|{rel}"
            ent = self._ledger_load(user_id).get(key)
            try:
                dirs = _Dirs(root_fd, comps[:-1])
                root_fd = -1  # the chain owns it now
            except FileNotFoundError:
                dirs = None  # landing folder missing: a normal upload below
            except _NotAFolder as exc:
                raise exc.refuse() from None
            if dirs is not None and ent is not None:
                try:
                    if not force and ent.get("size") == size \
                            and ent.get("mtime") == mtime and ent.get("landed_name"):
                        # The last upload of this file was saved aside: the
                        # untouched copy check must look at the name the file
                        # ACTUALLY landed under (never at the original name,
                        # which may hold a fifo/directory/link or somebody
                        # else's content). The recorded name is a bare
                        # filename the ledger itself stored on landing.
                        landed = ent["landed_name"]
                        if (isinstance(landed, str)
                                and "/" not in landed and "\0" not in landed):
                            st = _stat_name(dirs.fd, landed)
                            if (st is not None and statmod.S_ISREG(st.st_mode)
                                    and st.st_size == ent.get("landed_size")
                                    and st.st_mtime_ns == ent.get("landed_mtime_ns")
                                    and await self._hash_matches(dirs, landed, ent.get("sha256"))):
                                if landed != comps[-1]:
                                    # The copy on disk is under a saved-aside
                                    # name: the path handed to the agent must
                                    # be the file's REAL location, and the
                                    # result must say why the name differs.
                                    occ = _stat_name(dirs.fd, comps[-1])
                                    if occ is not None:
                                        reason = (f"the name {comps[-1]!r} is occupied by "
                                                  f"{self._describe_kind(occ.st_mode)}")
                                    else:
                                        reason = (f"the name {comps[-1]!r} is not where the "
                                                  f"file landed (it is at {landed!r})")
                                    base = str(visible).rsplit("/", 1)[0]
                                    real_visible = f"{base}/{landed}" if base else f"/{landed}"
                                    saved_as = (f"{reason}; the file is at {landed!r}")
                                else:
                                    real_visible = str(visible)
                                    saved_as = None
                                t = self._new(user_id=user_id, pair_id=pair_id, direction="up",
                                              local_path=rel, cloud_path=Path(real_visible),
                                              size=size, mtime_unix=mtime, received=size)
                                t.result = {"sha256": ent.get("sha256", ""), "fresh": True,
                                            "visible": real_visible}
                                if saved_as:
                                    t.result["saved_as"] = saved_as
                                t.finish(True)
                                return t
                        ent = None  # the saved-aside copy is gone or changed: normal upload
                    if ent is not None:
                        st = _stat_name(dirs.fd, comps[-1])
                        if (not force and ent.get("size") == size and ent.get("mtime") == mtime
                                and st is not None and statmod.S_ISREG(st.st_mode)
                                and st.st_size == ent.get("landed_size")
                                and st.st_mtime_ns == ent.get("landed_mtime_ns")
                                and await self._hash_matches(dirs, comps[-1], ent.get("sha256"))):
                            t = self._new(user_id=user_id, pair_id=pair_id, direction="up",
                                          local_path=rel, cloud_path=Path(visible),
                                          size=size, mtime_unix=mtime, received=size)
                            t.result = {"sha256": ent.get("sha256", ""), "fresh": True,
                                        "visible": str(visible)}
                            t.finish(True)
                            return t
                finally:
                    dirs.close()
            elif dirs is not None:
                dirs.close()

            # 4) An identical transfer already running? Join it instead of
            #    starting a second copy (the model may call the tool twice).
            for other in self._transfers.values():
                if (other.state == "active" and other.direction == "up" and other.user_id == user_id
                        and other.pair_id == pair_id and other.local_path == rel):
                    await self._check_stall(other)
                    if other.state == "active":
                        return other

            # 5) Open the landing directory chain (creating what is missing)
            #    and the anonymous temp file. Everything from here on happens
            #    relative to these handles.
            if root_fd < 0:
                root_fd = self._user_root_fd(user_id)
            try:
                dirs = _Dirs(root_fd, comps[:-1], create=True)
                root_fd = -1
            except FileNotFoundError as exc:
                raise BridgeProtocolError(CODE_NOT_FOUND, str(exc))
            except _NotAFolder as exc:
                raise exc.refuse() from None
            try:
                # A symlink at the final name must never be written through
                # or replaced: the upload lands under a free
                # "<name>.uploaded" name instead, the link is left exactly
                # as it is, and the result says so (see _land).
                free = shutil.disk_usage(f"/proc/self/fd/{dirs.fd}").free
                if size + DISK_RESERVE_BYTES > free:
                    t = self._advisory(
                        user_id, pair_id, "up", rel, str(visible), size,
                        f"not enough space in the cloud to receive this file ({size:,} bytes needed, "
                        f"{free:,} free, {DISK_RESERVE_BYTES:,} kept in reserve)")
                    dirs.close()
                    return t

                t = self._new(user_id=user_id, pair_id=pair_id, direction="up", local_path=rel,
                              cloud_path=Path(str(visible)), size=size, mtime_unix=mtime)
                t.result = {"visible": str(visible)}
                t.dirs = dirs
                t.sha = hashlib.sha256()
                try:
                    # O_TMPFILE: the file has no name, so nothing in the user's
                    # folder can redirect or replace what we write.
                    t.file_fd = os.open(".", os.O_RDWR | os.O_TMPFILE | os.O_CLOEXEC, 0o600,
                                        dir_fd=dirs.fd)
                except OSError as exc:
                    # The transfer and its dir handles are already registered:
                    # from here on a failure goes through the SAME teardown —
                    # finish() closes the handles exactly once and drops the
                    # transfer's references, so the background sweep never
                    # closes a recycled fd number. The transfer is returned
                    # (failed) instead of raising: the model gets FAILED with
                    # a plain reason (disk full, unsupported filesystem, ...)
                    # on THIS call, not "in progress" until the stall timeout.
                    t.finish(False, f"a temporary file could not be created in the cloud "
                                    f"({exc.strerror or exc}); the transfer was not started")
                    return t
                except BaseException:
                    # Unexpected (not an OS-level refusal): end the transfer
                    # the same way, then let it travel to the last-resort net.
                    t.finish(False, "the upload could not be started")
                    dirs = None  # finish() closed and dropped them; nothing left to close below
                    raise
            except BaseException:
                if dirs is not None:
                    dirs.close()
                raise
            try:
                # max_bytes rides along as the bridge-side last line of
                # defence: if the file grew past the limit between the stat
                # probe and now, the bridge refuses with 4003 instead of
                # streaming an over-limit file. That refusal is turned into
                # the same advisory the probe-time check produces.
                await self._call(user_id, pair_id, "transfer_upload",
                                 {"path": local_path, "max_bytes": self.max_bytes, **self._bridge_params(t)})
            except BridgeProtocolError as exc:
                t.finish(False, exc.message)  # release the temp fd and dir handles
                if exc.code == CODE_TOO_LARGE:
                    return self._advisory(
                        user_id, pair_id, "up", rel, str(visible), size,
                        f"file is over the {self.max_bytes:,}-byte transfer limit "
                        "(it grew between the size check and the upload start)")
                raise
            except BaseException:
                # OSError, cancellation, anything: the handles this transfer
                # already holds are released before the exception travels on.
                t.finish(False, "the upload could not be started")
                raise
            return t
        finally:
            if root_fd >= 0:
                os.close(root_fd)

    # ------------------------------------------------- start: folder upload
    # "Fetch this whole folder": list it first, decide whether it fits the
    # limits, and only then hand every file to the ordinary single-file
    # upload path — same ledger, same "already up to date" shortcut, same
    # keep-the-old-cloud-copy rules. Nothing here bypasses or re-implements
    # that path; it just drives it once per file, one file at a time.

    async def start_upload_dir(self, user_id: str, pair_id: str, local_path: str,
                               force: bool = False) -> Transfer:
        """Fetch every file under a folder. Returns ONE record for the whole
        batch (state active while it runs, done/failed at the end)."""
        try:
            man = await self._call(user_id, pair_id, "transfer_manifest", {"path": local_path})
        except BridgeProtocolError as exc:
            if exc.code == CODE_METHOD_NOT_FOUND:
                # Compatibility: the employee's machine runs a localoctop
                # program from before whole-folder fetches. That is a normal
                # answer ("ask the user to update, or fetch one file at a
                # time"), never a program error.
                return self._folder_advisory(
                    user_id, pair_id, local_path, str(local_path),
                    "this folder cannot be fetched in one call: the localoctop program on the "
                    "user's computer is an older version that does not support fetching a whole "
                    "folder. Nothing was sent.\n"
                    "Next step: ask the user to update the localoctop program on their computer, "
                    "or fetch the files one at a time with fetch_to_cloud.",
                    tail=False)
            raise
        if not isinstance(man, dict):
            raise BridgeProtocolError(CODE_INTERNAL, "the folder listing came back malformed")
        files = [f for f in (man.get("files") or []) if isinstance(f, dict)]
        skipped = int(man.get("skipped_non_regular") or 0)
        limit = int(man.get("file_limit") or 2000)
        over = bool(man.get("over_limit"))
        total = int(man.get("total_files") or len(files))
        total_bytes = int(man.get("total_bytes") or 0)
        folder_rel = str(man.get("path") or local_path)
        base = "" if folder_rel in ("", ".", "/") else folder_rel
        _, folder_vis = self._dest_for(user_id, (base + "/x") if base else "x", "x")
        folder_visible = str(folder_vis).rsplit("/", 1)[0] or "/"

        # A folder with only special files (or nothing) is a normal, finished
        # answer — there is simply nothing to send.
        if not files and not over:
            why = ("the folder is empty" if not skipped else
                   f"the folder holds no regular files ({skipped} symbolic link(s) or other "
                   f"special file(s) were skipped)")
            t = self._folder_advisory(
                user_id, pair_id, folder_rel, folder_visible,
                f"Nothing to send: {why}. Nothing was sent to the cloud.",
                tail=False)
            t.result.pop("advisory", None)
            t.state = "done"
            t.error = ""
            return t

        # Over the limits: a normal answer that says exactly what the folder
        # holds, that nothing was sent, and how to split the work.
        if over or total > limit:
            count = f"more than {limit:,}" if over else f"{total:,}"
            # Over the count cap the bridge only listed the first files:
            # whatever byte total it sent covers just those, so quoting a
            # size next to the real (larger) count would mislead — with
            # zero-byte files it even reads like a broken counter. The count
            # alone is the honest statement here.
            return self._folder_advisory(
                user_id, pair_id, folder_rel, folder_visible,
                f"NOT TRANSFERRED: the folder {base or '.'!r} holds {count} files; "
                f"the limit is {limit:,} files per fetch. Nothing was sent to the cloud.",
                await self._folder_subdirs(user_id, pair_id, local_path))

        if total_bytes > self.max_bytes:
            return self._folder_advisory(
                user_id, pair_id, folder_rel, folder_visible,
                f"NOT TRANSFERRED: the folder {base or '.'!r} holds {total:,} files totalling "
                f"{_human(total_bytes)}, over the {_human(self.max_bytes)} one-shot transfer "
                f"limit. Nothing was sent to the cloud.",
                await self._folder_subdirs(user_id, pair_id, local_path))

        # In the limits: one record for the batch, driven by a background task
        # so a long folder keeps answering "in progress" and stays pollable
        # through transfer_status, exactly like a single file.
        planned = []
        for f in files:
            rel = str(f.get("rel") or "")
            if not rel:
                continue
            rel = rel.replace("\\", "/")
            planned.append({
                "rel": rel,
                "local": f"{base}/{rel}" if base else rel,
                "size": int(f.get("size") or 0),
            })
        t = self._new(user_id=user_id, pair_id=pair_id, direction="up",
                      local_path=folder_rel, cloud_path=Path(folder_visible))
        t.result = {"visible": folder_visible, "folder": True}
        t.batch = {
            "folder": folder_rel, "visible": folder_visible, "files": planned,
            "total": len(planned), "total_bytes": total_bytes,
            "index": 0, "done": 0, "done_bytes": 0, "fresh": 0,
            "failed": [], "kept": [], "saved_as": [], "skipped": skipped,
            "current": "", "offline": False,
        }
        t.size = total_bytes
        task = asyncio.get_running_loop().create_task(
            self._run_folder_batch(t, user_id, pair_id, force))
        t.batch_task = task
        self._batch_tasks.add(task)
        task.add_done_callback(self._batch_tasks.discard)
        return t

    async def _folder_subdirs(self, user_id: str, pair_id: str, path: str) -> list[str]:
        """Direct sub-folder names of `path`, for "fetch one sub-folder at a
        time" advice. Best effort: a listing that fails just means no names."""
        try:
            res = await self._call(user_id, pair_id, "list_directory", {"path": path, "depth": 1})
        except BridgeProtocolError:
            return []
        out: list[str] = []
        for e in (res or {}).get("entries") or []:
            if not isinstance(e, dict) or not str(e.get("type", "")).startswith("dir"):
                continue
            name = str(e.get("name") or "")
            if name and "/" not in name and name not in ("", ".", "..") and name not in out:
                out.append(name)
        return out

    def _folder_advisory(self, user_id: str, pair_id: str, folder: str, visible: str,
                         text: str, subdirs: list[str] | None = None,
                         tail: bool = True) -> Transfer:
        """A finished, nothing-transferred record for a folder answer that hit
        a limit or an old client. Hitting a limit is a normal result with a
        way forward, so tools.py renders it as isError=false.

        tail=False is for texts that already carry their own next step (the
        empty-folder case, and the old-client explanation): appending the
        generic advice there would repeat what the text just said."""
        if tail and subdirs:
            shown = ", ".join(subdirs[:20])
            more = f" (and {len(subdirs) - 20} more)" if len(subdirs) > 20 else ""
            text += (f"\nWhat you can do instead: fetch one sub-folder at a time "
                     f"({shown}{more}), or fetch only the individual files you need.")
        elif tail:
            text += ("\nWhat you can do instead: fetch only the individual files you need, "
                     "one call each.")
        t = self._new(user_id=user_id, pair_id=pair_id, direction="up",
                      local_path=folder, cloud_path=Path(visible))
        t.result = {"advisory": True, "visible": visible, "batch_text": text}
        t.finish(False, text)
        return t

    async def _run_folder_batch(self, rec: Transfer, user_id: str, pair_id: str,
                                force: bool) -> None:
        """Drive one folder fetch: start each file's ordinary upload, wait for
        it to land, record the outcome, move on. A failure never stops the
        rest; the machine going away does."""
        batch = rec.batch or {}
        try:
            for i, spec in enumerate(batch["files"]):
                if rec.state != "active":
                    return  # aclose() ended the batch
                if self.shutdown_event.is_set():
                    # The service is going down: stop driving new files. A
                    # file transfer in flight would never finish (the bridge
                    # is about to be cut off), and finishing the batch
                    # record now lets aclose()'s own finish() be a no-op
                    # instead of an unexplained "adapter is shutting down"
                    # for a poll later.
                    batch["stopped"] = True
                    rec.touch()
                    return
                batch["index"] = i + 1
                batch["current"] = spec["local"]
                rec.touch()
                try:
                    ft = await self.start_upload(user_id, pair_id, spec["local"], force=force)
                except BridgeProtocolError as exc:
                    batch["failed"].append((spec["local"], exc.message))
                    if exc.code == CODE_NO_BRIDGE:
                        batch["offline"] = True
                        break
                    continue
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    batch["failed"].append((spec["local"], _plain(exc)))
                    continue
                if not await self._wait_batch_file(rec, ft):
                    # The batch was torn down (aclose) while this file ran.
                    rec.touch()
                    return
                if ft.state == "failed" and ft.offline:
                    batch["failed"].append((spec["local"], ft.error))
                    batch["offline"] = True
                    break
                self._record_file_outcome(batch, ft, spec["local"])
                rec.touch()
        except asyncio.CancelledError:
            # aclose() cancelled us: release what the current file still holds
            # (start_upload already finishes its own record on cancellation).
            batch["stopped"] = True
            rec.touch()
            raise
        finally:
            if rec.state == "active":
                self._finish_batch(rec)

    async def _wait_batch_file(self, rec: Transfer, ft: Transfer) -> bool:
        """Wait for one file of the batch to finish. Returns False when the
        batch itself was ended (aclose / shutdown), so the caller stops. The
        batch record is touched every round so the stall sweep can never
        mistake a long single file for a dead batch."""
        while ft.state == "active":
            if rec.state != "active":
                return False
            if self.shutdown_event.is_set():
                # The service is going down. wait() returns AT ONCE in this
                # state without yielding, so looping on would spin the loop
                # with the event loop fully hogged — aclose()'s cancel would
                # then never be delivered (a cancel only lands at an await
                # point) and every test / shutdown that awaits it would
                # hang. Treat shutdown as "the batch was ended" and stop.
                return False
            rec.touch()
            await self.wait(ft, 2.0)
        return True

    @staticmethod
    def _record_file_outcome(batch: dict[str, Any], ft: Transfer, local: str) -> None:
        if ft.state == "done" and ft.result.get("fresh"):
            batch["fresh"] += 1
        elif ft.state == "done":
            batch["done"] += 1
            batch["done_bytes"] += ft.size
        else:
            # A per-file advisory (over the limit / no cloud space) or a real
            # failure: recorded with its reason, the batch carries on.
            batch["failed"].append((local, ft.error or "the file could not be sent"))
        # Kept/saved-as names are recorded whatever the outcome — a file that
        # was already up to date can still have landed under a saved-as name
        # the model needs to know about.
        kept = ft.result.get("kept_as_list") or []
        if ft.result.get("kept_as"):
            if not kept:
                kept = [ft.result["kept_as"]]
            for name in kept:
                base = str(name).rsplit("/", 1)[-1]
                if base and base not in batch["kept"]:
                    batch["kept"].append(base)
        if ft.result.get("saved_as"):
            vis = str(ft.result.get("visible") or "")
            base = vis.rsplit("/", 1)[-1] if vis else ""
            if base and base not in batch["saved_as"]:
                batch["saved_as"].append(base)

    def _finish_batch(self, rec: Transfer) -> None:
        batch = rec.batch or {}
        ok = batch["done"] + batch["fresh"]
        batch["current"] = ""
        rec.result["batch_text"] = self._batch_text(rec)
        if ok == 0:
            rec.finish(False, "not one file of the folder could be sent: "
                              + (batch["failed"][0][1] if batch["failed"] else "unknown reason"))
        else:
            # At least one file landed: the call is a success, and the text
            # says what was partial about it (isError stays false).
            rec.finish(True)

    def _batch_text(self, rec: Transfer) -> str:
        """The finished folder result, kept inside the model-facing cap by
        shrinking the list of named failures until it fits.

        The cap is read at call time (not imported at module load) so it
        always follows the live value — the tool layer's own limit is the one
        source of truth for how much text the model may be handed."""
        from .tools import MODEL_RESULT_CAP_BYTES as cap
        b = rec.batch or {}
        show = 20
        while True:
            text = self._batch_text_with(b, show)
            if len(text.encode("utf-8", "replace")) <= cap or show <= 0:
                return text
            show //= 2

    def _batch_text_with(self, b: dict[str, Any], show: int) -> str:
        ok = b["done"] + b["fresh"]
        if ok == 0:
            head = "FAILED local → cloud (folder)"
        elif b["failed"]:
            head = "PART DONE local → cloud (folder)"
        else:
            head = "DONE local → cloud (folder)"
        stopped = (b["offline"] or b.get("stopped")) and not _all_done(b)
        if b["fresh"]:
            lines = [head + f": {b['done']:,} file(s) sent this time ({_human(b['done_bytes'])}); "
                            f"{b['fresh']:,} of the {b['total']:,} were already up to date in the cloud "
                            f"and were not re-sent."]
        else:
            lines = [head + f": {ok:,} of {b['total']:,} file(s) sent, {_human(b['done_bytes'])}."]
        if stopped:
            lines.append("The batch was stopped early: the user's computer went offline (or the "
                         "localoctop program was closed) part-way through, so the remaining "
                         "files were not attempted. Start it again when the computer is back.")
        lines.append(f"cloud folder: {b['visible']}")
        lines.append(f"local folder: {b['folder']}")
        if b["total"] == 0:
            lines.append("The folder holds no regular files to send.")
        if b["fresh"]:
            lines.append(f"{b['fresh']:,} file(s) were already up to date in the cloud "
                         f"(nothing re-sent).")
        if b["skipped"]:
            lines.append(f"{b['skipped']:,} symbolic link(s) or other special file(s) were "
                         f"skipped (only regular files are sent).")
        if b["failed"]:
            lines.append(f"{len(b['failed']):,} file(s) could not be sent:")
            for path, why in b["failed"][:show]:
                lines.append(f"  - {path}: {why}")
            if len(b["failed"]) > show:
                lines.append(f"  (another {len(b['failed']) - show:,} not listed)")
        if b["kept"]:
            lines.append("Previous cloud copies that were modified — or could not be confirmed "
                         "unmodified — were kept: "
                         + ", ".join(b["kept"][:show])
                         + (f" (and {len(b['kept']) - show} more)" if len(b["kept"]) > show else ""))
        if b["saved_as"]:
            lines.append("Some files were saved under a different name because the name was "
                         "taken: " + ", ".join(b["saved_as"][:show])
                         + (f" (and {len(b['saved_as']) - show} more)"
                            if len(b["saved_as"]) > show else ""))
        lines.append("Every file is under the cloud folder with the same layout it has on the "
                     "machine. Work on them there with your own file/shell tools.")
        if b["failed"] and ok > 0:
            lines.append("Next step: call fetch_to_cloud on this same folder again — the files "
                         "that already arrived will not be sent twice.")
        return "\n".join(lines)

    def _batch_progress_text(self, rec: Transfer) -> str:
        b = rec.batch or {}
        idx = b["index"]
        lines = [f"IN PROGRESS local → cloud (folder): file {idx:,} of {b['total']:,}, "
                 f"{_human(b['done_bytes'])} of {_human(b['total_bytes'])} sent so far."]
        if b["current"]:
            lines.append(f"current file: {b['current']}")
        if b["failed"]:
            lines.append(f"{len(b['failed']):,} file(s) failed so far (the batch carries on).")
        lines.append(f"cloud folder: {b['visible']}")
        lines.append(f"transfer_id: {rec.id}")
        lines.append("Call transfer_status with this transfer_id to keep waiting. Do NOT start "
                     "the same folder again — it is still running.")
        return "\n".join(lines)

    async def _stop_batch_tasks(self) -> None:
        """Cancel every running folder-fetch task and wait for each to exit.

        Cancellation is what makes a batch stop touching its file's handles;
        waiting for the tasks is what makes it safe for aclose() to close
        those handles afterwards. A task that refuses to exit within the
        shutdown window is logged and left to process exit (its record is
        still finished below, so the model is never left polling it)."""
        while self._batch_tasks:
            pending = [t for t in list(self._batch_tasks) if not t.done()]
            for task in pending:
                task.cancel()
            if not pending:
                break
            done, still = await asyncio.wait(pending, timeout=CLOSE_WAIT_SECONDS)
            for task in done:
                self._batch_tasks.discard(task)
            if still:
                logger.error("aclose: %d folder-fetch task(s) did not stop within %.1fs; "
                             "their records are finished anyway (process exit reclaims the fds)",
                             len(still), CLOSE_WAIT_SECONDS)
                for task in still:
                    self._batch_tasks.discard(task)
                break

    # ----------------------------------------------------- start: download
    async def start_download(self, user_id: str, pair_id: str, cloud_path: str,
                             local_path: str, overwrite: bool) -> Transfer:
        fd, dirs, st = self._open_agent_file(user_id, cloud_path)
        size = st.st_size
        if size > self.max_bytes:
            os.close(fd)
            dirs.close()
            return self._advisory(
                user_id, pair_id, "down", local_path or cloud_path.rsplit("/", 1)[-1] or "file",
                cloud_path, size,
                f"file is {size:,} bytes, over the {self.max_bytes:,}-byte transfer limit")
        t = self._new(user_id=user_id, pair_id=pair_id, direction="down",
                      local_path=local_path or cloud_path.rsplit("/", 1)[-1] or "file",
                      cloud_path=Path(cloud_path), size=size)
        t.dirs = dirs
        t.file_fd = fd
        try:
            # Hash the held fd, not the path: the digest is of the exact
            # file /content will serve, whatever the user does to the name.
            # The thread gets its own duplicated fd and closes it itself.
            t.expected_sha = await _run_owning_fd(_sha256_fd_own, os.dup(fd))
            acc = await self._call(user_id, pair_id, "transfer_download",
                                   {"path": t.local_path, "size": size, "sha256": t.expected_sha,
                                    "overwrite": bool(overwrite), **self._bridge_params(t)})
        except BaseException as exc:
            # Any failure after the handles were allocated — protocol error,
            # OSError, cancellation — ends the transfer and releases them.
            t.finish(False, getattr(exc, "message", None) or "the download could not be started")
            raise
        t.local_path = str(acc.get("path") or t.local_path)
        return t

    # -------------------------------------------------------------- status
    def get_for_user(self, user_id: str, transfer_id: str) -> Transfer:
        t = self._transfers.get(transfer_id)
        if t is None or t.user_id != user_id:
            raise BridgeProtocolError(
                CODE_NOT_FOUND, f"no transfer {transfer_id!r} (finished long ago, or the server restarted) — "
                                "start it again with fetch_to_cloud / deliver_to_local")
        return t

    async def wait(self, t: Transfer, seconds: float) -> None:
        """Wait up to `seconds` for the transfer to finish — or for the
        service to start shutting down, in which case return immediately so
        the tool call can answer (with a restart note) instead of being cut
        off mid-wait."""
        deadline = time.monotonic() + seconds
        # The shutdown event must wake this call even if it is sitting in a
        # wait when the signal arrives. Wait on the transfer's done-event
        # and the shutdown event together; the 2s slice keeps the stall
        # check cadence the old loop had.
        done_task = asyncio.create_task(t.done.wait())
        shut_task = asyncio.create_task(self.shutdown_event.wait())
        try:
            while t.state == "active":
                if self.shutdown_event.is_set():
                    return
                await self._check_stall(t)
                left = deadline - time.monotonic()
                if left <= 0 or t.state != "active":
                    return
                try:
                    # asyncio.wait (not gather): wait never cancels the
                    # tasks it watches, so a timed-out slice leaves both
                    # waiters alive for the next round. wait_for cancels the
                    # _first_of wrapper on timeout, which asyncio.wait
                    # tolerates (it just stops watching).
                    await asyncio.wait_for(
                        _first_of(done_task, shut_task), timeout=min(left, 2.0))
                except asyncio.TimeoutError:
                    continue
        finally:
            done_task.cancel()
            shut_task.cancel()

    def _agent_view(self, t: Transfer) -> str:
        """The path the agent should use, as seen from inside its folder."""
        if t.direction == "up":
            return str(t.result.get("visible") or "")
        return t.local_path

    def describe(self, t: Transfer) -> str:
        """Plain-text status for the model. Short on purpose."""
        what = "local → cloud" if t.direction == "up" else "cloud → local"
        if t.batch is not None:
            # A whole-folder fetch: its own progress/completion wording, kept
            # inside the model-facing cap by shrinking the listed names.
            if t.state == "active":
                return self._batch_progress_text(t)
            return str(t.result.get("batch_text") or t.error or "the folder fetch ended")
        if t.result.get("batch_text"):
            # A folder answer that never became a batch (empty folder, over
            # the limits, older client): the text is ready as it stands.
            return str(t.result["batch_text"])
        if t.result.get("advisory"):
            # A limit was hit: nothing moved, and the text must hand the
            # model a concrete next step, not a dead end.
            if t.direction == "up":
                path_line = f"local_path: {t.local_path}\n"
                alt = ("What you can do instead: ask the user to split or compress the file on their "
                       "machine and fetch the smaller part(s), or ask the administrator to raise the "
                       "transfer limit / free up cloud space.")
            else:
                path_line = f"cloud_path: {t.cloud_path}\n"
                alt = ("What you can do instead: split or compress the file here in the cloud "
                       "(with your command-line tools) and deliver the smaller part(s), or ask the "
                       "administrator to raise the transfer limit.")
            return (f"NOT TRANSFERRED {what}: {t.error}\n"
                    f"{path_line}"
                    f"size: {t.size:,} bytes\n"
                    f"{alt}")
        if t.state == "done" and t.direction == "up":
            fresh = " (cloud copy was already up to date — nothing re-sent)" if t.result.get("fresh") else ""
            kept = t.result.get("kept_as")
            # T5-6: say WHY the previous cloud copy was kept, truthfully. When
            # the ledger held no record (or the check was inconclusive) we do
            # NOT know whether the copy had been modified — claiming it had is
            # a false conclusion. Only a proven content change gets the
            # "had been modified" wording.
            unknown = set(t.result.get("kept_unknown") or [])
            kept_line = ""
            if kept:
                if kept in unknown:
                    kept_line = (f"A file with the same name already existed in the cloud and it "
                                 f"could not be confirmed whether it was the unmodified copy from "
                                 f"last time, so to avoid losing anything it was kept as {kept}.\n")
                else:
                    kept_line = f"The previous cloud copy had been modified and was kept as {kept}.\n"
            kept_list = t.result.get("kept_as_list") or []
            if len(kept_list) > 1:
                kept_line += "All kept copies: " + ", ".join(kept_list) + ".\n"
            saved_as = t.result.get("saved_as")
            saved_line = (f"Note: {saved_as}\n" if saved_as else "")
            return (f"DONE {what}{fresh}\n"
                    f"cloud_path: {self._agent_view(t)}\n"
                    f"local_path: {t.local_path}\n"
                    f"size: {t.size:,} bytes\n"
                    f"sha256: {t.result.get('sha256', '')}\n"
                    f"{kept_line}"
                    f"{saved_line}"
                    "The file is now on the cloud machine at cloud_path. Work on it there with your own "
                    "file/shell tools. It is a copy: the user's original stays untouched on their machine.\n"
                    "If the file is larger than 10 MB, process it with command-line tools (execute): "
                    "the platform's built-in search skips files over 10 MB.")
        if t.state == "done":
            if t.result.get("already_present"):
                # T6-1: a re-delivery whose earlier completion report was
                # lost — the file was already on the machine byte-identical,
                # so nothing was written and no "name (1).ext" duplicate was
                # made. Say exactly that.
                return (f"DONE {what}\n"
                        f"local_path: {t.result.get('path') or t.local_path}\n"
                        f"size: {t.size:,} bytes\n"
                        f"The file was already on the user's machine, exactly the same content — "
                        f"nothing was written and no second copy was made.")
            note = ""
            if t.result.get("replaced"):
                # T5-5: say where the old version ACTUALLY went. The current
                # client only overwrites after moving the old version into the
                # recycle bin; an OLD client could rename it aside instead, so
                # keep the "renamed:" rendering for compatibility with the
                # versions that still send it. An old client that reports only
                # `replaced` documented the bin as its first choice.
                set_aside = str(t.result.get("set_aside") or "")
                if set_aside.startswith("renamed:"):
                    note = (f" The old version could not be moved to the recycle bin and was "
                            f"renamed to {set_aside[len('renamed:'):]} instead (it sits next to "
                            f"the delivered file).")
                else:
                    note = " The previous version was moved to the recycle bin."
            return (f"DONE {what}\n"
                    f"local_path: {t.result.get('path') or t.local_path}\n"
                    f"size: {t.size:,} bytes\n"
                    f"The file is now on the user's machine.{note}")
        if t.state == "failed":
            return f"FAILED {what}: {t.error}"
        have = min(t.received + t.inflight, t.size)
        pct = (100.0 * have / t.size) if t.size else 0.0
        elapsed = max(time.monotonic() - t.created, 0.001)
        speed = have / elapsed
        eta = f", about {int((t.size - have) / speed) + 1}s left" if speed > 0 and t.size else ""
        idle = time.monotonic() - t.updated
        if self.shutdown_event.is_set():
            # The service is going down: this answer is the tool call's last
            # word, so it must carry the way forward by itself.
            return (f"IN PROGRESS {what}: {pct:.0f}% ({have:,} of {t.size:,} bytes)\n"
                    f"transfer_id: {t.id}\n"
                    "The localoctop service is restarting right now. Wait a few seconds, then call "
                    "transfer_status with this transfer_id to keep waiting; if the id is no longer "
                    "known after the restart, start the transfer again.")
        if idle > 20:
            # No bytes for a while: say so plainly instead of showing a stale
            # speed. The bridge keeps retrying on its own and resumes from
            # where it stopped; nothing has to be restarted.
            left = max(int(STALL_SECONDS - idle), 0)
            return (f"IN PROGRESS {what}: paused at {pct:.0f}% ({have:,} of {t.size:,} bytes) — no data "
                    f"for {int(idle)}s, the user's computer seems to be offline. It will resume by itself "
                    f"from this point when the connection is back (waiting up to {left}s more).\n"
                    f"transfer_id: {t.id}\n"
                    "Call transfer_status again to keep waiting. Do NOT start the same transfer again.")
        return (f"IN PROGRESS {what}: {pct:.0f}% ({have:,} of {t.size:,} bytes, "
                f"{speed / 1048576:.1f} MB/s{eta})\n"
                f"transfer_id: {t.id}\n"
                "Call transfer_status with this transfer_id to keep waiting. Do NOT start the same "
                "transfer again — it is still running.")

    # ----------------------------------------------------- landing (upload)
    @staticmethod
    def _free_name(dirs: _Dirs, name: str) -> str:
        """`name` if free below the verified dir handle, else name-1, -2…"""
        if _stat_name(dirs.fd, name) is None:
            return name
        for i in range(1, 1000):
            cand = f"{name}-{i}"
            if _stat_name(dirs.fd, cand) is None:
                return cand
        raise OSError(f"no free alternative name for {name!r}")

    @staticmethod
    def _describe_kind(st_mode: int) -> str:
        """Best-effort type word for a non-regular occupant."""
        if statmod.S_ISFIFO(st_mode):
            return "a named pipe (fifo)"
        if statmod.S_ISDIR(st_mode):
            return "a directory"
        if statmod.S_ISLNK(st_mode):
            return "a symbolic link"
        if statmod.S_ISSOCK(st_mode):
            return "a socket"
        if statmod.S_ISCHR(st_mode):
            return "a character device"
        if statmod.S_ISBLK(st_mode):
            return "a block device"
        return "not a regular file"

    def _save_aside(self, t: Transfer, final: str, reason: str) -> str:
        """Pick a free "<final>.uploaded" name, point the transfer's visible
        cloud_path at it so tools render the path where the file actually
        landed, and record the explanation for the result text."""
        saved = self._free_name(t.dirs, f"{final}.uploaded")  # type: ignore[arg-type]
        old_vis = str(t.result.get("visible") or str(t.cloud_path))
        base = old_vis.rsplit("/", 1)[0]
        t.result["visible"] = f"{base}/{saved}" if base else f"/{saved}"
        t.result["saved_as"] = f"{reason}; the file was saved as {saved!r} instead"
        return saved

    async def _land(self, t: Transfer, digest: str) -> tuple[os.stat_result, list[str]]:
        """Give the verified anonymous upload file its final name, never
        overwriting anything: the linkat fails with EEXIST while the name is
        taken, a name already taken is first moved aside atomically and
        overwrite-free (renameat2 RENAME_NOREPLACE), and only a moved-aside
        copy that provably IS the copy we landed last time (inode + sha256
        of its content both match the ledger record) is removed.

        A final name occupied by anything that is not a regular file (a
        fifo, directory, symlink, socket or device) never receives user
        content: that thing is never moved, deleted or opened; the upload
        lands as "<name>.uploaded" (numeric suffix when taken) and the
        result tells the agent so — a normal outcome, not an error (the
        transfer's cloud_path then points at the file's real location).

        No visible intermediate name ever exists: the file goes straight
        from anonymous (O_TMPFILE) to the final name. Returns (fstat of the
        landed fd, kept-as names of every copy moved aside — all of them,
        not just the last)."""
        dirs = t.dirs
        assert dirs is not None
        final = t.cloud_path.name
        st_occ = _stat_name(dirs.fd, final)
        if st_occ is not None and not statmod.S_ISREG(st_occ.st_mode):
            # Never touched: not moved, not deleted, not opened. The
            # upload lands under a free name; the result names both the
            # occupant's kind and the new name, and the transfer's
            # cloud_path now points at the file's real location.
            final = self._save_aside(
                t, final,
                f"the name {final!r} is occupied by "
                f"{self._describe_kind(st_occ.st_mode)}")
        idx_prev = self._ledger_load(t.user_id).get(f"{t.pair_id}|{t.local_path}")
        kept_list: list[str] = []
        for _ in range(20):
            try:
                os.link(f"/proc/self/fd/{t.file_fd}", final,
                        dst_dir_fd=dirs.fd, follow_symlinks=True)
                st = os.fstat(t.file_fd)
                # The bare name the file actually landed under: the ledger
                # stores it so the "still our untouched copy" shortcut
                # checks the file's real location, not the original name.
                t.result["landed_name"] = final
                if kept_list:
                    # The agent-visible paths of the kept copies: the
                    # transfer's visible path with the final component
                    # swapped for each kept-as name.
                    vis = str(t.result.get("visible") or "")
                    base = vis.rsplit("/", 1)[0] if "/" in vis else ""
                    t.result["kept_as_list"] = [
                        f"{base}/{k}" if base else f"/{k}" for k in kept_list]
                    t.result["kept_as"] = t.result["kept_as_list"][-1]
                    if t.result.get("kept_unknown"):
                        t.result["kept_unknown"] = [
                            f"{base}/{k}" if base else f"/{k}"
                            for k in t.result["kept_unknown"]]
                return st, kept_list
            except FileExistsError:
                pass  # the name is taken: move the occupant aside below
            st_dst = _stat_name(dirs.fd, final)
            if st_dst is None:
                continue  # the occupant vanished between the two syscalls
            if not statmod.S_ISREG(st_dst.st_mode):
                # A non-regular file appeared at the name after we checked
                # (or mid-retry): same rule as above — never touch it, save
                # the upload aside under a free name and keep landing.
                final = self._save_aside(
                    t, final,
                    f"the name {final!r} is occupied by "
                    f"{self._describe_kind(st_dst.st_mode)}")
                continue
            try:
                kept_as = self._keep_cloud_edited(dirs, final)
            except FileNotFoundError:
                # Someone else moved the occupant away first: not a failure —
                # retry the landing link against the now-free (or newly
                # occupied) name.
                continue
            dropped, why = await self._drop_if_our_last_copy(dirs, kept_as, idx_prev)
            if dropped:
                continue  # it was our own untouched copy: nothing to report
            kept_list.append(kept_as)
            if why == "unknown":
                # T5-6: kept because we could NOT confirm what it was (no
                # record, or the check was inconclusive) — the result text
                # must say that, not claim the copy had been modified.
                unknown = t.result.setdefault("kept_unknown", [])
                unknown.append(kept_as)
        raise OSError(
            f"the landing path {final!r} stayed occupied through 20 attempts"
            + (f"; the conflicting copies were moved aside to: {', '.join(kept_list)}"
               if kept_list else ""))

    async def _drop_if_our_last_copy(self, dirs: _Dirs, kept_as: str,
                                     idx_prev: Any) -> tuple[bool, str]:
        """Delete the moved-aside occupant ONLY if it is provably the copy
        this adapter landed last time, untouched: its content hashes to the
        ledger's sha256, fstat before AND after hashing shows the same size,
        st_mtime_ns and st_ctime_ns (a rewrite mid-hash means "cannot prove
        untouched" — keep it), and the name still resolves to the very inode
        that was hashed. In every other case — the content was edited, the
        ledger has no record, the inode changed, any step fails — the file is
        kept and the transfer result names it.

        The before/after fstat does NOT close the race: a write landing
        between the last check and the unlink would still be lost. It only
        catches the obvious cases, and whenever in doubt the file is kept —
        that residual risk is accepted.

        Returns (removed, why_kept): why_kept is "modified" when the content
        provably differs from the recorded copy, otherwise "unknown" — the
        truthful distinction the result text needs (T5-6): "we could not
        confirm whether it had been changed" is NOT "it had been changed"."""
        if not isinstance(idx_prev, dict) or not idx_prev.get("sha256"):
            return False, "unknown"  # no record of it: it is somebody's work — keep it
        try:
            fd = _open_regular_file(dirs.fd, kept_as)
        except OSError:
            return False, "unknown"
        try:
            st = os.fstat(fd)
            try:
                dup = os.dup(fd)
            except OSError:
                return False, "unknown"
            digest = await _run_owning_fd(_sha256_fd_own, dup)
            if digest != idx_prev["sha256"]:
                return False, "modified"  # content changed since we landed it: cloud work — keep it
            st_after = os.fstat(fd)
            if (st.st_size, st.st_mtime_ns, st.st_ctime_ns) != \
                    (st_after.st_size, st_after.st_mtime_ns, st_after.st_ctime_ns):
                return False, "unknown"  # rewritten while we hashed: cannot prove untouched
            # The stat between hashing and unlinking narrows the race, it
            # does not close it: the agent could still swap this
            # timestamped keep-as name in the microsecond between the two
            # calls, in which case we would remove what it just placed
            # there. That residual risk is accepted.
            st2 = _stat_name(dirs.fd, kept_as)
            if st2 is None or (st2.st_ino, st2.st_dev) != (st.st_ino, st.st_dev):
                return False, "unknown"
            os.unlink(kept_as, dir_fd=dirs.fd)
            logger.info("removed the untouched previous copy of the landed file (kept-as %s)", kept_as)
            return True, ""
        except OSError:
            return False, "unknown"
        finally:
            os.close(fd)

    # ----------------------------------------------- bridge-facing HTTP API
    async def _put_chunk(self, t: Transfer, request: Request, offset: int):
        """Receive and apply one upload chunk. Every failure this method
        anticipates is answered with a specific status and (where the
        transfer cannot continue) an abort; anything it does NOT anticipate
        propagates to the route's last-resort handler."""
        if t.direction != "up" or t.state != "active":
            return JSONResponse({"error": f"transfer is {t.state}", "received": t.received}, status_code=410)
        declared = int(request.headers.get("content-length") or 0)
        if declared > MAX_CHUNK_BYTES:
            return JSONResponse({"error": "chunk too large"}, status_code=413)
        # Buffer the whole chunk first: a chunk is applied all-or-nothing,
        # so a connection cut mid-chunk leaves the file at a clean offset.
        buf = bytearray()
        try:
            async for piece in request.stream():
                buf.extend(piece)
                # Bytes are arriving: that is activity and progress even
                # though the chunk is only applied once it is complete (on a
                # slow link one chunk takes tens of seconds).
                t.inflight = len(buf)
                t.touch()
                if len(buf) > MAX_CHUNK_BYTES:
                    return JSONResponse({"error": "chunk too large"}, status_code=413)
        except (ClientDisconnect, ConnectionError, OSError):
            # The bridge's connection dropped while the chunk was arriving —
            # the normal case resume exists for. Nothing of this chunk is
            # applied (received/sha stay as they were), the transfer stays
            # active, and the bridge re-sends this chunk from t.received when
            # it is back. NOT an internal error: never the last-resort
            # handler, never an ERROR log. The answer is irrelevant (the
            # peer is gone) but must not raise into it either.
            logger.info("transfer %s: the bridge disconnected while a chunk was arriving "
                        "(at offset %d, %d bytes of this chunk discarded); "
                        "the transfer stays active for resume", t.id, t.received, len(buf))
            t.inflight = 0
            t.touch()
            return JSONResponse({"error": "client disconnected", "received": t.received},
                                status_code=499)
        if declared and len(buf) != declared:
            return JSONResponse({"error": "short chunk", "received": t.received}, status_code=400)
        async with t.lock:
            if t.state != "active":
                return JSONResponse({"error": f"transfer is {t.state}"}, status_code=410)
            if offset != t.received:
                return JSONResponse({"error": "offset mismatch", "received": t.received}, status_code=409)
            if t.received + len(buf) > t.size:
                self._abort(t, "the local file grew during the transfer; please fetch it again")
                return JSONResponse({"error": "exceeds declared size"}, status_code=413)
            try:
                # All chunks go to the one anonymous temp fd held since
                # the start; the folder's names cannot redirect this.
                # The worker thread writes through its OWN duplicated fd
                # and closes it itself: if this coroutine is cancelled
                # and the transfer's handles are released meanwhile, the
                # thread's write still lands on the file it was meant
                # for — never on whatever recycled the fd number.
                try:
                    wfd = os.dup(t.file_fd)
                except OSError as exc:
                    raise OSError(f"could not duplicate the temp fd: {exc}") from exc
                try:
                    await _run_owning_fd(_pwrite_own, wfd, bytes(buf), t.received)
                except asyncio.CancelledError:
                    # The thread finishes on its own fd (it is allowed
                    # to — the temp data dies with the transfer).
                    raise
            except OSError as exc:
                self._abort(t, f"could not write to cloud storage: {exc}")
                return JSONResponse({"error": "storage write failed"}, status_code=507)
            t.sha.update(buf)
            t.received += len(buf)
            t.inflight = 0
            t.touch()
        return {"received": t.received}

    async def _complete(self, t: Transfer, request: Request):
        """Apply the bridge's completion report (integrity check, landing,
        ledger). Handled failures abort the transfer with a specific reason;
        anything unanticipated propagates to the route's last-resort handler,
        which ends the transfer as failed instead of leaving it 'active'."""
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return JSONResponse({"error": "invalid JSON"}, status_code=400)
        async with t.lock:
            if t.state != "active":
                return {"state": t.state}
            if not body.get("ok"):
                self._abort(t, str(body.get("error") or "the local machine reported a failure")[:500])
                return {"state": t.state}
            if t.direction == "down":
                t.result = {"path": str(body.get("path") or ""), "replaced": bool(body.get("replaced"))}
                # T5-5 / T6-1: how the landing actually went — the old version
                # went to the recycle bin or was renamed aside ("renamed:<rel>"),
                # or the file was already on the machine byte-identical and
                # nothing was written. Old clients send neither key; the
                # describe text then falls back to the recycle-bin wording only
                # when `replaced` is set.
                if body.get("set_aside"):
                    t.result["set_aside"] = str(body["set_aside"])
                if body.get("already_present"):
                    t.result["already_present"] = True
                t.received = t.size
                t.finish(True)
                return {"state": t.state}
            # Integrity is checked against what actually landed: the
            # anonymous fd is the only writer (O_TMPFILE has no name, so
            # nothing else in the user's folder can reach it), and fstat
            # confirms exactly `size` bytes made it to disk.
            try:
                st = os.fstat(t.file_fd)
            except OSError as exc:
                self._abort(t, f"could not verify the received file: {exc}")
                return {"state": t.state}
            digest = t.sha.hexdigest()
            if (t.received != t.size or st.st_size != t.size
                    or int(body.get("size", -1)) != t.size or body.get("sha256") != digest):
                self._abort(t, "integrity check failed — the copy that reached the cloud does not match "
                               "the local file; please fetch it again")
                return {"state": t.state}
            try:
                # Set the local file's mtime on our own fd, before the
                # file gets any name the user could swap.
                if t.mtime_unix:
                    os.utime(t.file_fd, ns=(t.mtime_unix * 1_000_000_000,) * 2)
                # Match the platform's other files (0644), not the 0600
                # an anonymous O_TMPFILE starts with.
                os.fchmod(t.file_fd, 0o644)
                st_final, _kept = await self._land(t, digest)
            except OSError as exc:
                self._abort(t, f"could not put the file in place in the cloud: {exc}")
                return {"state": t.state}
            # The file landed: the transfer IS a success from here on.
            # The ledger only powers the "already up to date" shortcut,
            # so a failure to persist it (state disk full, the ledger
            # directory swapped out, ...) must not fail the request or
            # strand the transfer: log it and finish normally.
            try:
                async with self._ledger_lock(t.user_id):
                    ledger = self._ledger_load(t.user_id)
                    ledger[f"{t.pair_id}|{t.local_path}"] = {
                        "size": t.size, "mtime": t.mtime_unix, "sha256": digest,
                        "landed_size": st_final.st_size,
                        "landed_mtime_ns": st_final.st_mtime_ns,
                        # The bare filename the file actually landed
                        # under: when the upload was saved aside this is
                        # the .uploaded name, and the "still our
                        # untouched copy" shortcut must check THAT name,
                        # never the original one.
                        "landed_name": t.result.get("landed_name") or t.cloud_path.name,
                        "at": int(time.time())}
                    self._ledger_save(t.user_id, ledger)
            except Exception:  # noqa: BLE001
                logger.warning("could not persist the transfer ledger for user %r; "
                               "the landed file is unaffected", t.user_id, exc_info=True)
            t.result = {**t.result, "sha256": digest}
            t.finish(True)
        return {"state": t.state}

    def _auth(self, request: Request, transfer_id: str) -> Transfer | JSONResponse:
        raw = request.headers.get("authorization", "")
        token = raw[7:].strip() if raw.lower().startswith("bearer ") else None
        try:
            user_id = self.settings.token_store.authenticate(KIND_BRIDGE, token)
        except BridgeProtocolError:
            return JSONResponse({"error": "authentication failed"}, status_code=401)
        t = self._transfers.get(transfer_id)
        if t is None:
            return JSONResponse({"error": "unknown transfer"}, status_code=404)
        ticket = request.headers.get("x-transfer-ticket", "")
        if t.user_id != user_id or not secrets.compare_digest(ticket, t.ticket):
            return JSONResponse({"error": "forbidden"}, status_code=403)
        return t

    def build_router(self) -> APIRouter:
        r = APIRouter()
        base = self.url_base

        @r.get(base + "/{tid}")
        async def status(tid: str, request: Request):
            t = self._auth(request, tid)
            if isinstance(t, JSONResponse):
                return t
            return {"state": t.state, "received": t.received, "size": t.size}

        @r.put(base + "/{tid}/chunk")
        async def put_chunk(tid: str, request: Request, offset: int = 0):
            t = self._auth(request, tid)
            if isinstance(t, JSONResponse):
                return t
            try:
                return await self._put_chunk(t, request, offset)
            except Exception:
                # Unexpected (not one of the handled protocol/storage cases
                # inside _put_chunk): the bridge gets a 5xx AND the transfer
                # is ended as failed — it must never sit "active" while the
                # model keeps polling. The raw exception goes to the log
                # only; the model sees plain language plus a reference id.
                ref = secrets.token_hex(4)
                logger.error("internal error receiving a chunk for transfer %s (user %r, ref %s)",
                             t.id, t.user_id, ref, exc_info=True)
                self._fail_unexpected(t, "receiving the file", ref)
                return JSONResponse({"error": f"internal error (ref {ref})"}, status_code=500)

        @r.get(base + "/{tid}/content")
        async def content(tid: str, request: Request):
            t = self._auth(request, tid)
            if isinstance(t, JSONResponse):
                return t
            if t.direction != "down" or t.state != "active":
                return JSONResponse({"error": f"transfer is {t.state}"}, status_code=410)
            start = 0
            m = re.match(r"bytes=(\d+)-", request.headers.get("range", ""))
            if m:
                start = int(m.group(1))
            if start > t.size:
                return JSONResponse({"error": "range not satisfiable"}, status_code=416)

            async def body():
                # Reads go through the fd captured at start_download: even if
                # the source path was renamed or replaced by a link since,
                # the bytes served are the file that was verified then. Each
                # worker-thread read uses its own duplicated fd (closed by
                # the thread), so a finished/cancelled transfer closing its
                # handles can never redirect an in-flight read.
                pos = start
                try:
                    while True:
                        try:
                            rfd = os.dup(t.file_fd)
                        except OSError:
                            return
                        data = await _run_owning_fd(_pread_own, rfd, 1024 * 1024, pos)
                        if not data:
                            return
                        pos += len(data)
                        t.received = max(t.received, pos)
                        t.touch()
                        try:
                            yield data
                        except (ClientDisconnect, ConnectionError, OSError,
                                GeneratorExit, asyncio.CancelledError):
                            # The bridge stopped reading (network cut, client
                            # closed, server shutting down): EXPECTED — the
                            # bridge resumes from t.received when it is back.
                            # The transfer stays active; nothing is failed,
                            # no ERROR is logged.
                            logger.info("transfer %s: the bridge disconnected while content "
                                        "was being served (at offset %d); "
                                        "the transfer stays active for resume", t.id, pos)
                            return
                except (ClientDisconnect, ConnectionError, OSError):
                    # A source-read failure that is really the connection
                    # going away: same expected case as above.
                    logger.info("transfer %s: connection lost while serving content "
                                "(at offset %d); the transfer stays active for resume", t.id, pos)
                    return
                except Exception:
                    # An unexpected failure mid-stream: the response headers
                    # are already sent, so the HTTP answer can only be cut —
                    # but the transfer must still be ended as failed (never
                    # left "active") and the failure logged with a reference.
                    ref = secrets.token_hex(4)
                    logger.error("internal error serving content of transfer %s (user %r, ref %s)",
                                 t.id, t.user_id, ref, exc_info=True)
                    self._fail_unexpected(t, "sending the file", ref)
                    return

            return StreamingResponse(body(), status_code=206, media_type="application/octet-stream", headers={
                "Content-Range": f"bytes {start}-{max(t.size - 1, 0)}/{t.size}",
                "Content-Length": str(t.size - start),
            })

        @r.post(base + "/{tid}/complete")
        async def complete(tid: str, request: Request):
            t = self._auth(request, tid)
            if isinstance(t, JSONResponse):
                return t
            # Register this coroutine's task so aclose() can cancel the
            # completion flow if it does not exit its lock in time.
            t.completion_task = asyncio.current_task()
            try:
                return await self._complete(t, request)
            except Exception:
                # Unexpected (not one of the handled cases inside _complete):
                # same rule as the chunk route — 5xx to the bridge AND the
                # transfer ended as failed with a plain-language reason, so
                # the model is never stuck polling an "active" record.
                ref = secrets.token_hex(4)
                logger.error("internal error completing transfer %s (user %r, ref %s)",
                             t.id, t.user_id, ref, exc_info=True)
                self._fail_unexpected(t, "finishing the transfer", ref)
                return JSONResponse({"error": f"internal error (ref {ref})"}, status_code=500)
            finally:
                t.completion_task = None

        return r


def _pread_own(fd: int, n: int, offset: int) -> bytes:
    """os.pread on a duplicated fd the worker thread owns end to end (see
    _sha256_fd_own for why). Returns b"" on error: a failed read ends the
    stream instead of killing the worker with an unraisable exception."""
    try:
        return os.pread(fd, n, offset)
    except OSError:
        return b""
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def _pwrite_own(fd: int, data: bytes, offset: int) -> int:
    """os.pwrite on a duplicated fd the worker thread owns end to end (see
    _sha256_fd_own for why). Writes the WHOLE buffer: pwrite(2) may legally
    accept only part of it, and taking a partial write as a full one would
    leave a hole in the file while the checksum and the byte count say
    "complete" — the worst outcome (a corrupt file reported as success).
    Loops until every byte is on disk; a write that makes no progress (0
    bytes) or raises is an OSError, so the chunk — and the transfer — fail
    instead of silently truncating."""
    try:
        view = memoryview(data)
        written = 0
        while written < len(view):
            n = os.pwrite(fd, view[written:], offset + written)
            if n <= 0:
                raise OSError(f"short write to cloud storage: {written} of {len(view)} bytes written")
            written += n
        return written
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
