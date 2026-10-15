import json
import platform
import socket
import psutil


def get_host_info() -> str:
    """
    Retrieve and return host system information as a formatted JSON string.
    """
    host_info = {
        "hostname": socket.gethostname(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "memory": str(round(psutil.virtual_memory().total / (1024.0**3))) + " GB",
    }
    return json.dumps(host_info, indent=4)

if __name__ == "__main__":
    print(get_host_info())