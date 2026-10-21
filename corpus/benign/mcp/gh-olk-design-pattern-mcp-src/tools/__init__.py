"""Tool factory functions for the MCP tool surface.

DP-4: Factory Pattern — consistent tool creation with proper initialization
DP-5: Dependency Injection — constructor injection of dependencies

Nine tools: the four pipeline tools (``select_design_patterns``, ``analyze_design``,
``generate_design``, ``evaluate_design``), the two catalog tools (``list_design_patterns``,
``get_design_pattern``) and the async job trio (``submit_design_job``, ``get_design_status``,
``cancel_design``).
"""

from __future__ import annotations

import asyncio

from src.config import TasksConfig
from src.patterns.loader import PatternLoader
from src.pipeline import CancellationToken, DesignPipeline
from src.tools.analyze import analyze_design_tool
from src.tools.cancel_design import cancel_design_tool
from src.tools.design import select_design_patterns_tool
from src.tools.evaluate import evaluate_design_tool
from src.tools.generate import generate_design_tool
from src.tools.get_design_status import get_design_status_tool
from src.tools.patterns import get_design_pattern_tool, list_design_patterns_tool
from src.tools.submit_design_job import submit_design_job_tool


def create_all_tools(
    pipeline: DesignPipeline,
    pattern_loader: PatternLoader,
    tasks_config: TasksConfig | None = None,
    *,
    job_tasks: dict[str, tuple[asyncio.Task[None], CancellationToken]] | None = None,
) -> dict[str, object]:
    """Create every MCP tool instance with its dependencies (DP-4, DP-5).

    Args:
        pipeline: the selection pipeline the phase tools delegate to.
        pattern_loader: the joined catalog for the read-only pattern tools.
        tasks_config: heartbeat settings (``None`` applies the defaults).
        job_tasks: shared ``{job_id: (task, cancellation_token)}`` registry of the job trio.

    Returns:
        Mapping of tool name → tool instance, keyed by the registered MCP tool name.
    """
    jt = job_tasks if job_tasks is not None else {}
    return {
        "select_design_patterns": select_design_patterns_tool(pipeline, tasks_config=tasks_config),
        "analyze_design": analyze_design_tool(pipeline, tasks_config=tasks_config),
        "generate_design": generate_design_tool(
            pipeline, pattern_loader, tasks_config=tasks_config
        ),
        "evaluate_design": evaluate_design_tool(pipeline, tasks_config=tasks_config),
        "list_design_patterns": list_design_patterns_tool(pattern_loader),
        "get_design_pattern": get_design_pattern_tool(pattern_loader),
        "submit_design_job": submit_design_job_tool(
            pipeline, tasks_config=tasks_config, job_tasks=jt
        ),
        "get_design_status": get_design_status_tool(),
        "cancel_design": cancel_design_tool(job_tasks=jt),
    }
