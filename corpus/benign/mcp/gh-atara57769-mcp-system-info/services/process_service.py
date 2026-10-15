import os
from typing import Any, Dict
import logging
import services.system_info_service as system_info
from utils import validation as validation

logger = logging.getLogger(__name__)


def get_system_info():
    logger.info("Fetching system information")
    return system_info.get_system_info()


def get_high_resource_usage():
    logger.info("Checking high resource usage processes")

    high_usage = system_info.check_high_resource_usage()
    logger.debug(f"Found {len(high_usage)} high usage processes")

    safe_processes = validation.get_safe_to_terminate_process(high_usage)

    processes_dict = []
    for proc in safe_processes:
        processes_dict.append(proc.to_dict())

    logger.info(f"{len(processes_dict)} processes are safe to terminate")

    return processes_dict


def terminate_process_with_validation(pid: int) -> Dict[str, Any]:
    logger.info(f"Termination requested for PID {pid}")

    proc_info = system_info.create_process_info(pid)

    # safety validation
    is_safe, reason = validation.is_process_safe_to_terminate(proc_info)

    if not is_safe:
        logger.warning(f"Termination blocked for PID {pid}. Reason: {reason}")
        return {
            "success": False,
            "message": reason,
            "pid": pid,
        }

    success = system_info.terminate_process(pid)

    if success:
        logger.info(f"Process {pid} terminated successfully")
    else:
        logger.error(f"Failed to terminate process {pid}")

    return {
        "success": success,
        "pid": pid,
        "message": "Process terminated" if success else "Failed to terminate process",
    }


def get_processes():
    logger.info("Fetching all processes")

    processes = system_info.get_processes()

    result = {
        "count": len(processes),
        "processes": [p.to_dict() for p in processes],
    }

    logger.debug(f"Returned {result['count']} processes")

    return result
