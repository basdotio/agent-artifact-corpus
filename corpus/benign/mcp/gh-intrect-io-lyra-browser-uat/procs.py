"""Child processes that are stopped as a group.

A harness brain is three processes deep — the harness, the MCP server it
spawns, the browser the server launches — and the batch runner adds a fourth
level above them. Signalling only the direct child leaves the rest running if it
ignores the signal or is killed: the server and its browser would be orphaned
with a profile locked. Each child is started in a session of its own, so its
process group is exactly its descendants, and the group is what gets
interrupted, then killed.

POSIX only (``start_new_session``, ``killpg``).
"""

from __future__ import annotations

import asyncio
import os
import signal
from typing import Any

POLL_S = 0.2
# After the direct child is gone, how long its descendants get to leave on their own
# before they are terminated, and then killed.
LINGER_S = 3.0
KILL_AFTER_S = 3.0


async def spawn(argv: list[str], **kwargs: Any) -> asyncio.subprocess.Process:
    """Start ``argv`` as the leader of a new session (so its pgid is its pid)."""
    return await asyncio.create_subprocess_exec(*argv, start_new_session=True, **kwargs)


_HAVE_PROC = os.path.isdir("/proc/self")


def group_alive(pgid: int) -> bool:
    """Whether any process of the group still runs.

    ``killpg(pgid, 0)`` answers on every POSIX system. Where ``/proc`` exists (Linux) a
    group holding only zombies — orphans nobody reaped — is told apart and counts as gone;
    without it (macOS) a zombie keeps the group "alive" until init reaps it, which is
    quick, and every wait here is bounded either way."""
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    if not _HAVE_PROC:
        return True
    return any(_running(pid) for pid in _members(pgid))


def _members(pgid: int) -> list[int]:
    found: list[int] = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return [pgid]  # no /proc: killpg(…, 0) already said something is there
    for name in entries:
        if not name.isdigit():
            continue
        try:
            stat = open(f"/proc/{name}/stat", encoding="utf-8").read()
        except OSError:
            continue
        # pid (comm) state ppid pgrp ...; comm may contain spaces and parentheses.
        fields = stat[stat.rfind(")") + 2 :].split()
        if len(fields) > 2 and int(fields[2]) == pgid:
            found.append(int(name))
    return found


def _running(pid: int) -> bool:
    try:
        stat = open(f"/proc/{pid}/stat", encoding="utf-8").read()
    except OSError:
        return False
    return stat[stat.rfind(")") + 2 :].split()[0] != "Z"


def _signal_group(pgid: int, sig: signal.Signals) -> bool:
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        return False
    return True


async def _wait_gone(pgid: int, seconds: float) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    while group_alive(pgid):
        if loop.time() >= deadline:
            return False
        await asyncio.sleep(POLL_S)
    return True


async def stop_group(proc: asyncio.subprocess.Process, *, grace_s: float) -> None:
    """Interrupt the whole group, give it ``grace_s`` to wind down, then kill what is left.

    Interrupting first lets a harness end its turn and close its MCP server, which closes
    the browser properly; the kill is for one that is stuck. Reaps the direct child.
    """
    pgid = proc.pid
    if _signal_group(pgid, signal.SIGINT):
        # The leader's own exit is what the caller waits on; the group is what must go.
        try:
            await asyncio.wait_for(proc.wait(), timeout=grace_s)
        except TimeoutError:
            pass
        if not await _wait_gone(pgid, max(0.0, LINGER_S)):
            _signal_group(pgid, signal.SIGKILL)
    if proc.returncode is None:
        await proc.wait()
    await _wait_gone(pgid, KILL_AFTER_S)


async def reap_group(pgid: int) -> None:
    """After a child exited on its own: whatever it left behind goes too.

    A harness that finished but did not close its server would otherwise leave a browser
    open on the run's profile.
    """
    if await _wait_gone(pgid, LINGER_S):
        return
    _signal_group(pgid, signal.SIGTERM)
    if await _wait_gone(pgid, KILL_AFTER_S):
        return
    _signal_group(pgid, signal.SIGKILL)
    await _wait_gone(pgid, KILL_AFTER_S)
