"""Goals tools (7 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_goals",
            description="Get goals for a workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "include_completed": {
                        "type": "boolean",
                        "description": "Include completed goals"
                    }
                },
                "required": ["workspace_id"]
            }
        ),
        Tool(
            name="get_goal",
            description="Get a specific goal",
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
            name="create_goal",
            description="Create a new goal",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Goal name"
                    },
                    "due_date": {
                        "type": "integer",
                        "description": "Due date timestamp"
                    },
                    "description": {
                        "type": "string",
                        "description": "Goal description"
                    },
                    "rem_owners": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Owner user IDs"
                    },
                    "color": {
                        "type": "string",
                        "description": "Goal color"
                    }
                },
                "required": ["workspace_id", "name"]
            }
        ),
        Tool(
            name="update_goal",
            description="Update a goal",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "string",
                        "description": "Goal ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "New goal name"
                    },
                    "due_date": {
                        "type": "integer",
                        "description": "Due date timestamp"
                    },
                    "description": {
                        "type": "string",
                        "description": "New goal description"
                    },
                    "rem_owners": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Owner user IDs"
                    },
                    "color": {
                        "type": "string",
                        "description": "Goal color"
                    },
                    "add_to_user_favorites": {
                        "type": "boolean",
                        "description": "Add to user favorites"
                    }
                },
                "required": ["goal_id"]
            }
        ),
        Tool(
            name="get_goal_key_results",
            description="Get key results for a goal",
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
            name="create_goal_key_result",
            description="Create a key result for a goal",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "string",
                        "description": "Goal ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Key result name"
                    },
                    "type": {
                        "type": "string",
                        "description": "Key result type (number, currency, percentage, automatic, manual)"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit (for number type)"
                    },
                    "steps_start": {
                        "type": "integer",
                        "description": "Starting value"
                    },
                    "steps_end": {
                        "type": "integer",
                        "description": "Target value"
                    },
                    "steps_current": {
                        "type": "integer",
                        "description": "Current value"
                    },
                    "task_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs to link"
                    },
                    "list_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List IDs to link"
                    }
                },
                "required": ["goal_id", "name", "type"]
            }
        ),
        Tool(
            name="update_goal_key_result",
            description="Update a goal key result",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "string",
                        "description": "Goal ID"
                    },
                    "key_result_id": {
                        "type": "string",
                        "description": "Key result ID"
                    },
                    "steps_current": {
                        "type": "integer",
                        "description": "Current value"
                    }
                },
                "required": ["goal_id", "key_result_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Goals category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_goals":
        workspace_id = arguments["workspace_id"]
        params = {}
        if "include_completed" in arguments:
            params["include_completed"] = arguments["include_completed"]
        response = await client.get(f"/team/{workspace_id}/goal", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_goal":
        goal_id = arguments["goal_id"]
        response = await client.get(f"/goal/{goal_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_goal":
        workspace_id = arguments["workspace_id"]
        data = {"name": arguments["name"]}
        for key in ["due_date", "description", "rem_owners", "color"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.post(f"/team/{workspace_id}/goal", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_goal":
        goal_id = arguments["goal_id"]
        data = {}
        for key in ["name", "due_date", "description", "rem_owners", "color", "add_to_user_favorites"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.put(f"/goal/{goal_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_goal_key_results":
        goal_id = arguments["goal_id"]
        response = await client.get(f"/goal/{goal_id}/key_result")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_goal_key_result":
        goal_id = arguments["goal_id"]
        data = {
            "name": arguments["name"],
            "type": arguments["type"]
        }
        for key in ["unit", "steps_start", "steps_end", "steps_current", "task_ids", "list_ids"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.post(f"/goal/{goal_id}/key_result", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_goal_key_result":
        goal_id = arguments["goal_id"]
        key_result_id = arguments["key_result_id"]
        data = {"steps_current": arguments["steps_current"]}
        response = await client.put(f"/goal/{goal_id}/key_result/{key_result_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
