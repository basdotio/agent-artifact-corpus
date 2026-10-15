"""Time Tracking tools (5 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_time_entries",
            description="Get time entries with filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team ID"
                    },
                    "start_date": {
                        "type": "integer",
                        "description": "Start date timestamp"
                    },
                    "end_date": {
                        "type": "integer",
                        "description": "End date timestamp"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Assignee user ID"
                    },
                    "include_task_tags": {
                        "type": "boolean",
                        "description": "Include task tags"
                    },
                    "include_location_names": {
                        "type": "boolean",
                        "description": "Include location names"
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space ID filter"
                    },
                    "folder_id": {
                        "type": "string",
                        "description": "Folder ID filter"
                    },
                    "list_id": {
                        "type": "string",
                        "description": "List ID filter"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task ID filter"
                    }
                },
                "required": ["team_id"]
            }
        ),
        Tool(
            name="get_time_entry",
            description="Get a specific time entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team ID"
                    },
                    "timer_id": {
                        "type": "string",
                        "description": "Timer ID"
                    }
                },
                "required": ["team_id", "timer_id"]
            }
        ),
        Tool(
            name="start_time_entry",
            description="Start a timer for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team ID"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task ID"
                    },
                    "billable": {
                        "type": "boolean",
                        "description": "Is billable"
                    },
                    "description": {
                        "type": "string",
                        "description": "Timer description"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Timer tags"
                    },
                    "tid": {
                        "type": "string",
                        "description": "Time tracking ID"
                    }
                },
                "required": ["team_id", "task_id"]
            }
        ),
        Tool(
            name="stop_time_entry",
            description="Stop a running timer",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team ID"
                    },
                    "timer_id": {
                        "type": "string",
                        "description": "Timer ID"
                    }
                },
                "required": ["team_id", "timer_id"]
            }
        ),
        Tool(
            name="update_time_entry",
            description="Update a time entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team ID"
                    },
                    "timer_id": {
                        "type": "string",
                        "description": "Timer ID"
                    },
                    "description": {
                        "type": "string",
                        "description": "New description"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "New tags"
                    },
                    "billable": {
                        "type": "boolean",
                        "description": "Is billable"
                    },
                    "start": {
                        "type": "integer",
                        "description": "Start time timestamp"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Duration in milliseconds"
                    }
                },
                "required": ["team_id", "timer_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Time Tracking category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_time_entries":
        team_id = arguments["team_id"]
        params = {"team_id": team_id}
        for key in ["start_date", "end_date", "assignee", "include_task_tags", "include_location_names",
                   "space_id", "folder_id", "list_id", "task_id"]:
            if key in arguments:
                params[key] = arguments[key]
        response = await client.get("/team/{}/time_entries".format(team_id), params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_time_entry":
        team_id = arguments["team_id"]
        timer_id = arguments["timer_id"]
        response = await client.get(f"/team/{team_id}/time_entries/{timer_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "start_time_entry":
        team_id = arguments["team_id"]
        data = {"tid": arguments["task_id"]}
        if "billable" in arguments:
            data["billable"] = arguments["billable"]
        if "description" in arguments:
            data["description"] = arguments["description"]
        if "tags" in arguments:
            data["tags"] = arguments["tags"]
        if "tid" in arguments:
            data["tid"] = arguments["tid"]
        response = await client.post(f"/team/{team_id}/time_entries/start", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "stop_time_entry":
        team_id = arguments["team_id"]
        timer_id = arguments["timer_id"]
        response = await client.post(f"/team/{team_id}/time_entries/stop/{timer_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_time_entry":
        team_id = arguments["team_id"]
        timer_id = arguments["timer_id"]
        data = {}
        for key in ["description", "tags", "billable", "start", "duration"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.put(f"/team/{team_id}/time_entries/{timer_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
