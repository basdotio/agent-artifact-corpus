from dataclasses import dataclass, asdict
from typing import Dict, Any
@dataclass(frozen=True)
class SystemInfo:
    """
    Represents system information.
    This is a model to hold the results of system info retrieval.
    """
    system: str
    node_name: str
    release: str
    version: str
    machine: str
    processor: str
    cpu_cores: int
    logical_cpus: int
    ram: float  # GB
    disk_usage: float  # Percentage
    cpu_usage: float  # Percentage
    memory_usage: float  # Percentage
    network_sent: float  # MB
    network_recv: float  # MB
    uptime: float  # Boot time (timestamp)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to plain dict for further usage or embedding.
        """
        return asdict(self)
