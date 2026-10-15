"""Delete Operations tools (7 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="delete_space",
            description="Delete a space",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space ID"
                    }
                },
                "required": ["space_id"]
            }
        ),
        Tool(
            name="delete_folder",
            description="Delete a folder",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_id": {
                        "type": "string",
                        "description": "Folder ID"
                    }
                },
                "required": ["folder_id"]
            }
        ),
        Tool(
            name="delete_list",
            description="Delete a list",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "List ID"
                    }
                },
                "required": ["list_id"]
            }
        ),
        Tool(
            name="delete_task",
            description="Delete a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="delete_comment",
            description="Delete a comment",
            inputSchema={
                "type": "object",
                "properties": {
                    "comment_id": {
                        "type": "string",
                        "description": "Comment ID"
                    }
                },
                "required": ["comment_id"]
            }
        ),
        Tool(
            name="delete_goal",
            description="Delete a goal",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "string",
                        "description": "Goal ID"
                    }
                },
                "required": ["goal_id"]
            }
        ),
        Tool(
            name="delete_key_result",
            description="Delete a key result",
            inputSchema={
                "type": "object",
                "properties": {
                    "key_result_id": {
                        "type": "string",
                        "description": "Key result ID"
                    }
                },
                "required": ["key_result_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Delete Operations category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "delete_space":
        space_id = arguments["space_id"]
        response = await client.delete(f"/space/{space_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Space deleted"}, indent=2))]

    elif name == "delete_folder":
        folder_id = arguments["folder_id"]
        response = await client.delete(f"/folder/{folder_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Folder deleted"}, indent=2))]

    elif name == "delete_list":
        list_id = arguments["list_id"]
        response = await client.delete(f"/list/{list_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "List deleted"}, indent=2))]

    elif name == "delete_task":
        task_id = arguments["task_id"]
        response = await client.delete(f"/task/{task_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Task deleted"}, indent=2))]

    elif name == "delete_comment":
        comment_id = arguments["comment_id"]
        response = await client.delete(f"/comment/{comment_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Comment deleted"}, indent=2))]

    elif name == "delete_goal":
        goal_id = arguments["goal_id"]
        response = await client.delete(f"/goal/{goal_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Goal deleted"}, indent=2))]

    elif name == "delete_key_result":
        key_result_id = arguments["key_result_id"]
        response = await client.delete(f"/key_result/{key_result_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Key result deleted"}, indent=2))]

    return None
