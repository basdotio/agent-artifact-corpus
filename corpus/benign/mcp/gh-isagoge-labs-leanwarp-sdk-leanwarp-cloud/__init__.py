"""Client for hosted LeanWarp; mathematical execution remains server-side."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("leanwarp-sdk")
except PackageNotFoundError:  # Imported from a source tree without installation.
    __version__ = "0.0.0"

from .client import LeanWarpCloud, LeanWarpCloudError, OperationTimeout
from .config import load_client
from .outcome import OperationOutcome
from .project import UploadPlan, collect_lean_sources, plan_upload
from .session import ProjectSession, SessionError, UsageError, WaitError

__all__ = [
    "LeanWarpCloud",
    "LeanWarpCloudError",
    "OperationOutcome",
    "OperationTimeout",
    "ProjectSession",
    "SessionError",
    "UploadPlan",
    "UsageError",
    "WaitError",
    "__version__",
    "collect_lean_sources",
    "load_client",
    "plan_upload",
]
