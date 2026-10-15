from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    status: str
    cpu_usage: float
    memory_usage: float

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ProcessInfo object to a dictionary for further usage or embedding.
        """
        return asdict(self)


