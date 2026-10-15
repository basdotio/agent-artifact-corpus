"""Own CLI descendants: suspended Windows launch into kill-on-close Job Object."""
from __future__ import annotations

import ctypes
import os
import signal


class ProcessOwner:
    def __init__(self):
        self.job = None
        if os.name == "nt":
            import win32job
            self.job = win32job.CreateJobObject(None, "")
            info = win32job.QueryInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation)
            info["BasicLimitInformation"]["LimitFlags"] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation, info)

    def launch_options(self):
        return {"creationflags": 0x08000004} if os.name == "nt" else {"start_new_session": True}

    def attach(self, process):
        self.pid = process.pid
        if os.name == "nt":
            import win32api
            import win32job
            handle = win32api.OpenProcess(0x0100 | 0x0800 | 0x0001, False, self.pid)
            try:
                win32job.AssignProcessToJobObject(self.job, handle)
                resume = ctypes.WinDLL("ntdll").NtResumeProcess
                resume.argtypes = [ctypes.c_void_p]
                resume.restype = ctypes.c_long
                if resume(int(handle)) != 0:
                    raise RuntimeError("could not resume isolated CLI")
            finally:
                handle.Close()

    def close(self):
        if self.job is not None:
            self.job.Close()
            self.job = None
        elif os.name != "nt" and hasattr(self, "pid"):
            try:
                os.killpg(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
