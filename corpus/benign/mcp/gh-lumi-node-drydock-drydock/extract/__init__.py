"""Component extraction: turn a boundary into a standalone package.

`boundaries` answers "where can I cut?"; this answers "cut it, and tell me
what breaks". Planning and execution are separate steps -- see
`drydock.extract.planner` and `drydock.extract.engine`.
"""

from __future__ import annotations

from .engine import ExtractionError, ExtractionResult, execute_plan
from .models import Breakage, ExtractionPlan, PlannedFile
from .planner import plan_extraction, select_by_cluster, select_by_dir, select_by_files
from .rewriters import rewriter_for

__all__ = [
    "Breakage",
    "ExtractionError",
    "ExtractionPlan",
    "ExtractionResult",
    "PlannedFile",
    "execute_plan",
    "plan_extraction",
    "rewriter_for",
    "select_by_cluster",
    "select_by_dir",
    "select_by_files",
]
