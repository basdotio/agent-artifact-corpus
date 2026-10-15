"""Tool category modules.

Each module exports TOOLS (a list of mcp.types.Tool schemas) and an async
handle(name, arguments) coroutine that returns a result if it owns that tool
name, or None so the caller can try the next category.
"""
from . import (
    workspace,
    tasks,
    time_tracking,
    goals,
    custom_fields,
    views,
    tags,
    statuses,
    webhooks,
    documents,
    checklists,
    task_templates,
    members,
    shared_hierarchy,
    bulk_operations,
    automations,
    enhanced_templates,
    delete_operations,
    dashboard_analytics,
)

CATEGORIES = [
    workspace,
    tasks,
    time_tracking,
    goals,
    custom_fields,
    views,
    tags,
    statuses,
    webhooks,
    documents,
    checklists,
    task_templates,
    members,
    shared_hierarchy,
    bulk_operations,
    automations,
    enhanced_templates,
    delete_operations,
    dashboard_analytics,
]
