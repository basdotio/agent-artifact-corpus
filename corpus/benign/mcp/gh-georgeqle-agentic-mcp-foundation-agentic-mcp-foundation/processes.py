"""Recover ownership using kernel process birth time and executable identity."""

import ctypes
import json
import os
import platform
import signal
import subprocess
import time
from functools import lru_cache
from pathlib import Path

from .transport import atomic_json


def _linux_identity(pid):
    # starttime plus boot identity prevents PID reuse from granting ownership.
    root = Path("/proc") / str(pid)
    fields = (root / "stat").read_text().rsplit(")", 1)[1].split()
    if fields[0] == "Z":
        raise ProcessLookupError("Process is a zombie")
    return {
        "pid": pid,
        "start": fields[19],
        "executable": str((root / "exe").resolve(strict=True)),
        "boot": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
    }


class _ProcBSDInfo(ctypes.Structure):
    # Darwin <sys/proc_info.h>, proc_bsdinfo / PROC_PIDTBSDINFO (3).
    _fields_ = (
        [
            (name, ctypes.c_uint32)
            for name in (
                "flags",
                "status",
                "xstatus",
                "pid",
                "ppid",
                "uid",
                "gid",
                "ruid",
                "rgid",
                "svuid",
                "svgid",
                "rfu_1",
            )
        ]
        + [("comm", ctypes.c_char * 16), ("name", ctypes.c_char * 32)]
        + [
            (name, ctypes.c_uint32)
            for name in (
                "nfiles",
                "pgid",
                "pjobc",
                "e_tdev",
                "e_tpgid",
            )
        ]
        + [
            ("nice", ctypes.c_int32),
            ("start_sec", ctypes.c_uint64),
            ("start_usec", ctypes.c_uint64),
        ]
    )


@lru_cache(maxsize=1)
def _darwin_boot():
    return subprocess.check_output(
        ["/usr/sbin/sysctl", "-n", "kern.bootsessionuuid"], timeout=5, text=True
    ).strip()


def _darwin_identity(pid):
    lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    lib.proc_pidinfo.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint64,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    lib.proc_pidinfo.restype = ctypes.c_int
    lib.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    lib.proc_pidpath.restype = ctypes.c_int
    info = _ProcBSDInfo()
    if lib.proc_pidinfo(pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info)) != ctypes.sizeof(info):
        raise ProcessLookupError("Cannot verify process birth identity")
    if info.pid != pid or info.status == 5:  # SZOMB
        raise ProcessLookupError("Process exited")
    path = ctypes.create_string_buffer(4096)
    if lib.proc_pidpath(pid, path, len(path)) <= 0:
        raise ProcessLookupError("Cannot verify process executable")
    boot = _darwin_boot()
    if not boot:
        raise ProcessLookupError("Cannot verify boot identity")
    return {
        "pid": pid,
        "start": f"{info.start_sec}:{info.start_usec}",
        "executable": os.fsdecode(path.value),
        "boot": boot,
    }


def identity(pid):
    system = platform.system()
    if system == "Linux":
        return _linux_identity(pid)
    if system == "Darwin":
        return _darwin_identity(pid)
    raise OSError(f"Process recovery is unsupported on {system}")


def remember(path, process):
    try:
        record = identity(process.pid)
    except (OSError, ValueError, subprocess.SubprocessError):
        return
    atomic_json(path, record)


class RecoveredProcess:
    def __init__(self, record):
        self.record, self.pid = record, record["pid"]

    def poll(self):
        try:
            return None if identity(self.pid) == self.record else 0
        except (OSError, ValueError, subprocess.SubprocessError):
            return 0

    def terminate(self):
        if self.poll() is None:
            os.kill(self.pid, signal.SIGTERM)

    def kill(self):
        if self.poll() is None:
            os.kill(self.pid, signal.SIGKILL)

    def wait(self, timeout):
        deadline = time.monotonic() + timeout
        while self.poll() is None:
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired("recovered process", timeout)
            time.sleep(0.05)
        return 0


def recover(path):
    try:
        process = RecoveredProcess(json.loads(path.read_text()))
        return process if process.poll() is None else None
    except (OSError, ValueError, KeyError, TypeError):
        return None
