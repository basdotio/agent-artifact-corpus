"""Built-in analyzers.

Importing this module registers the built-ins. They go through exactly the same
`registry.register` call a third-party plugin uses -- there is no privileged
internal path, which is the point: if the built-ins can be expressed through
the plugin contract, so can yours.
"""

from __future__ import annotations

from ..core.registry import registry
from .architecture import ArchitectureAnalyzer
from .boundaries import BoundariesAnalyzer
from .codemap import CodemapAnalyzer
from .context import ContextAnalyzer
from .dependencies import DependenciesAnalyzer
from .git_history import GitHistoryAnalyzer
from .interfaces import InterfacesAnalyzer
from .platforms import PlatformsAnalyzer
from .security import SecurityAnalyzer
from .structure import StructureAnalyzer

for _analyzer in (
    CodemapAnalyzer(),
    BoundariesAnalyzer(),
    ArchitectureAnalyzer(),
    InterfacesAnalyzer(),
    DependenciesAnalyzer(),
    StructureAnalyzer(),
    PlatformsAnalyzer(),
    GitHistoryAnalyzer(),
    SecurityAnalyzer(),
    ContextAnalyzer(),
):
    registry.register(_analyzer)

__all__ = [
    "ArchitectureAnalyzer",
    "BoundariesAnalyzer",
    "CodemapAnalyzer",
    "ContextAnalyzer",
    "DependenciesAnalyzer",
    "GitHistoryAnalyzer",
    "InterfacesAnalyzer",
    "PlatformsAnalyzer",
    "SecurityAnalyzer",
    "StructureAnalyzer",
]
