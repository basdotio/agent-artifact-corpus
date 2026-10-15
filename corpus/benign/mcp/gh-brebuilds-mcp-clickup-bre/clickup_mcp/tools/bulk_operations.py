"""Bulk Operations tools (3 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="bulk_create_tasks",
            description="Batch create multiple tasks efficiently",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "List ID"
                    },
                    "tasks": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Array of task objects to create"
                    }
                },
                "required": ["list_id", "tasks"]
            }
        ),
        Tool(
            name="bulk_update_tasks",
            description="Batch update multiple tasks efficiently",
            inputSchema={
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Array of task objects with id and fields to update"
                    }
                },
                "required": ["tasks"]
            }
        ),
        Tool(
            name="bulk_delete_tasks",
            description="Batch delete multiple tasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of task IDs to delete"
                    }
                },
                "required": ["task_ids"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Bulk Operations category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "bulk_create_tasks":
        list_id = arguments["list_id"]
        tasks = arguments["tasks"]
        results = []
        for task_data in tasks:
            try:
                response = await client.post(f"/list/{list_id}/task", json=task_data)
                results.append({"success": True, "data": response.json()})
            except Exception as e:
                results.append({"success": False, "error": str(e), "task": task_data})
        return [TextContent(type="text", text=json.dumps({"results": results, "total": len(tasks), "successful": sum(1 for r in results if r.get("success"))}, indent=2))]

    elif name == "bulk_update_tasks":
        tasks = arguments["tasks"]
        results = []
        for task_update in tasks:
            try:
                task_id = task_update.pop("id")
                response = await client.put(f"/task/{task_id}", json=task_update)
                results.append({"success": True, "task_id": task_id, "data": response.json()})
            except Exception as e:
                results.append({"success": False, "error": str(e), "task": task_update})
        return [TextContent(type="text", text=json.dumps({"results": results, "total": len(tasks), "successful": sum(1 for r in results if r.get("success"))}, indent=2))]

    elif name == "bulk_delete_tasks":
        task_ids = arguments["task_ids"]
        results = []
        for task_id in task_ids:
            try:
                response = await client.delete(f"/task/{task_id}")
                results.append({"success": True, "task_id": task_id})
            except Exception as e:
                results.append({"success": False, "task_id": task_id, "error": str(e)})
        return [TextContent(type="text", text=json.dumps({"results": results, "total": len(task_ids), "successful": sum(1 for r in results if r.get("success"))}, indent=2))]

    return None
