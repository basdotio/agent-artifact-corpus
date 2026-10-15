"""Interruptible POSIX stdin for graceful stdio transport shutdown."""

import io
import os
import select
import sys
from contextlib import contextmanager


class _InterruptibleStdin(io.RawIOBase):
    """Read stdin without leaving a blocked worker thread after shutdown."""

    def __init__(self, file_descriptor, stop_event):
        self._file_descriptor = file_descriptor
        self._stop_event = stop_event

    def fileno(self):
        """Prevent MCP SDK fd claiming so it uses this public stream adapter."""
        raise io.UnsupportedOperation('interruptible stdin has no claimable descriptor')

    def readable(self):
        return True

    def readinto(self, buffer):
        while not self._stop_event.is_set():
            try:
                readable, _, _ = select.select([self._file_descriptor], [], [], 0.1)
                if readable:
                    data = os.read(self._file_descriptor, len(buffer))
                    buffer[: len(data)] = data
                    return len(data)
            except InterruptedError:
                continue
        return 0

    def close(self):
        if not self.closed:
            os.close(self._file_descriptor)
        super().close()


@contextmanager
def interruptible_stdin(stop_event):
    """Replace stdin with an interruptible adapter until FastMCP exits.

    Falls back to the normal stdin path when stdin has no real file descriptor
    (e.g. pytest capture, Windows).

    ponytail: POSIX select only; add a Windows-native cancellable reader if Windows
    stdio must support graceful signal shutdown.
    """
    if os.name != 'posix':
        yield
        return
    try:
        original_fileno = sys.stdin.fileno()
    except io.UnsupportedOperation:
        yield
        return
    original_stdin = sys.stdin
    file_descriptor = os.dup(original_fileno)
    raw_stream = _InterruptibleStdin(file_descriptor, stop_event)
    sys.stdin = io.TextIOWrapper(io.BufferedReader(raw_stream), encoding='utf-8', errors='replace')
    try:
        yield
    finally:
        sys.stdin.close()
        sys.stdin = original_stdin
