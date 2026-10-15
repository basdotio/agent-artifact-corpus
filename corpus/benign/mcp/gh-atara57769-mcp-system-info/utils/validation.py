import os
from typing import Tuple

import psutil

from models.process_info import ProcessInfo


CRITICAL_WINDOWS = {
    "system",
    "svchost.exe",
    "wininit.exe",
    "winlogon.exe",
    "csrss.exe",
    "services.exe",
}

CRITICAL_LINUX = {
    "systemd",
    "init",
}


def is_process_safe_to_terminate(process_info: ProcessInfo) -> Tuple[bool, str]:
    try:
        # Zombie processes are always safe
        if process_info.status == psutil.STATUS_ZOMBIE:
            return True, "Zombie process"

        name = (process_info.name or "").lower()

        # Never kill PID 0/1
        if process_info.pid in (0, 1):
            return False, "Critical system PID"

        # Never kill ourselves
        if process_info.pid == os.getpid():
            return False, "Cannot terminate current process"

        # Windows critical processes
        if name in CRITICAL_WINDOWS:
            return False, "Critical Windows process"

        # Linux critical processes
        if name in CRITICAL_LINUX:
            return False, "Critical Linux process"

        return True, "Safe to terminate"

    except AttributeError:
        return False, "Invalid process information"

    except psutil.NoSuchProcess:
        return False, "Process no longer exists"

    except psutil.AccessDenied:
        return False, "Access denied"


def get_safe_to_terminate_process(processes):
    safe_processes = []

    for proc in processes:
        is_safe, _ = is_process_safe_to_terminate(proc)

        if is_safe:
            safe_processes.append(proc)

    return safe_processes


def user_confirmed(action: str, confirmed: bool) -> bool:
    if not confirmed:
        raise ValueError(f"User confirmation required before performing: {action}")
    return True
