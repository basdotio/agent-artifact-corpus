"""Dashboard & Analytics tools (4 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_workspace_dashboard",
            description="Get dashboard data for a workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "date_from": {
                        "type": "integer",
                        "description": "Start date timestamp"
                    },
                    "date_to": {
                        "type": "integer",
                        "description": "End date timestamp"
                    }
                },
                "required": ["workspace_id"]
            }
        ),
        Tool(
            name="get_space_dashboard",
            description="Get dashboard data for a space",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space ID"
                    },
                    "date_from": {
                        "type": "integer",
                        "description": "Start date timestamp"
                    },
                    "date_to": {
                        "type": "integer",
                        "description": "End date timestamp"
                    }
                },
                "required": ["space_id"]
            }
        ),
        Tool(
            name="get_task_analytics",
            description="Get analytics data for tasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space ID filter (optional)"
                    },
                    "date_from": {
                        "type": "integer",
                        "description": "Start date timestamp"
                    },
                    "date_to": {
                        "type": "integer",
                        "description": "End date timestamp"
                    }
                },
                "required": ["workspace_id"]
            }
        ),
        Tool(
            name="get_time_tracking_report",
            description="Get time tracking report data",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team ID"
                    },
                    "date_from": {
                        "type": "integer",
                        "description": "Start date timestamp"
                    },
                    "date_to": {
                        "type": "integer",
                        "description": "End date timestamp"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Filter by assignee ID"
                    }
                },
                "required": ["team_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Dashboard & Analytics category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_workspace_dashboard":
        workspace_id = arguments["workspace_id"]
        params = {}
        if "date_from" in arguments:
            params["date_from"] = arguments["date_from"]
        if "date_to" in arguments:
            params["date_to"] = arguments["date_to"]
        response = await client.get(f"/team/{workspace_id}/dashboard", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_space_dashboard":
        space_id = arguments["space_id"]
        params = {}
        if "date_from" in arguments:
            params["date_from"] = arguments["date_from"]
        if "date_to" in arguments:
            params["date_to"] = arguments["date_to"]
        response = await client.get(f"/space/{space_id}/dashboard", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_task_analytics":
        workspace_id = arguments["workspace_id"]
        params = {}
        if "space_id" in arguments:
            params["space_id"] = arguments["space_id"]
        if "date_from" in arguments:
            params["date_from"] = arguments["date_from"]
        if "date_to" in arguments:
            params["date_to"] = arguments["date_to"]
        response = await client.get(f"/team/{workspace_id}/task/analytics", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_time_tracking_report":
        team_id = arguments["team_id"]
        params = {}
        if "date_from" in arguments:
            params["date_from"] = arguments["date_from"]
        if "date_to" in arguments:
            params["date_to"] = arguments["date_to"]
        if "assignee" in arguments:
            params["assignee"] = arguments["assignee"]
        response = await client.get(f"/team/{team_id}/time_entries/report", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
