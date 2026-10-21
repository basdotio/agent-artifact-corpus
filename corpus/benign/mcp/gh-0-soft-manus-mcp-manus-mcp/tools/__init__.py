"""Tool registration package. Import side-effect loads all tool modules."""

from manus_mcp.tools.registry import ToolCtx, ToolDef, all_tools, manus_tool

__all__ = ["ToolCtx", "ToolDef", "all_tools", "load_all_tool_modules", "manus_tool"]


def load_all_tool_modules() -> None:
    """Import every tool module so @manus_tool decorators fire."""
    from manus_mcp.tools import (  # noqa: F401
        agents,
        browser,
        composite,
        connectors,
        files,
        projects,
        skills,
        tasks,
        usage,
        webhooks,
        website,
    )
    from manus_mcp.webhook_receiver import tools as _webhook_receiver_tools  # noqa: F401
