from typing import Dict, Any, List
import platform
import psutil

from utils import validation
from models.process_info import ProcessInfo
from models.system_info import SystemInfo


def get_system_info():
    net_io = psutil.net_io_counters()
    system_info = SystemInfo(
        system=platform.system(),
        node_name=platform.node(),
        release=platform.release(),
        version=platform.version(),
        machine=platform.machine(),
        processor=platform.processor(),
        cpu_cores=psutil.cpu_count(logical=False),
        logical_cpus=psutil.cpu_count(logical=True),
        ram=psutil.virtual_memory().total / (1024**3),
        disk_usage=psutil.disk_usage("/").percent,
        cpu_usage=psutil.cpu_percent(interval=0),
        memory_usage=psutil.virtual_memory().percent,
        network_sent=net_io.bytes_sent / (1024**2),
        network_recv=net_io.bytes_recv / (1024**2),
        uptime=psutil.boot_time(),
    )
    return system_info


def create_process_info(pid: int) -> ProcessInfo:
    proc = psutil.Process(pid)
    return ProcessInfo(
        pid=proc.pid,
        name=proc.name(),
        status=proc.status(),
        cpu_usage=proc.cpu_percent(interval=0),
        memory_usage=proc.memory_info().rss / (1024**2),  # MB
    )


def check_high_resource_usage():
    high_usage = []

    # Get all processes with basic info
    for proc in psutil.process_iter(["pid", "name"]):
        pid = proc.info["pid"]

        # Check memory

        proc_obj = psutil.Process(pid)
        memory_mb = proc_obj.memory_info().rss / (1024**2)

        if memory_mb > 500:
            process_info = create_process_info(pid)
            if process_info:
                high_usage.append(process_info)

    return high_usage


def terminate_process(pid: int) -> bool:
    try:
        proc = psutil.Process(pid)
        proc.terminate()

        try:
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            proc.kill()

        return True

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def get_processes():
    """
    Return all running processes.
    """
    result: List[ProcessInfo] = []

    for proc in psutil.process_iter(["pid"]):
        try:
            info = create_process_info(proc.pid)
            result.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return result
