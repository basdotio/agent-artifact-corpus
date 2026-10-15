"""Task Management tools (14 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_tasks",
            description="Get tasks from a list, folder, or space with filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "List ID (optional)"
                    },
                    "folder_id": {
                        "type": "string",
                        "description": "Folder ID (optional)"
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space ID (optional)"
                    },
                    "archived": {
                        "type": "boolean",
                        "description": "Include archived tasks"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number"
                    },
                    "order_by": {
                        "type": "string",
                        "description": "Order by field (id, created, updated, due_date)"
                    },
                    "reverse": {
                        "type": "boolean",
                        "description": "Reverse order"
                    },
                    "subtasks": {
                        "type": "boolean",
                        "description": "Include subtasks"
                    },
                    "statuses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by statuses"
                    },
                    "include_closed": {
                        "type": "boolean",
                        "description": "Include closed tasks"
                    },
                    "assignees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by assignee IDs"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags"
                    },
                    "due_date_gt": {
                        "type": "integer",
                        "description": "Due date greater than (timestamp)"
                    },
                    "due_date_lt": {
                        "type": "integer",
                        "description": "Due date less than (timestamp)"
                    },
                    "date_created_gt": {
                        "type": "integer",
                        "description": "Date created greater than (timestamp)"
                    },
                    "date_created_lt": {
                        "type": "integer",
                        "description": "Date created less than (timestamp)"
                    },
                    "date_updated_gt": {
                        "type": "integer",
                        "description": "Date updated greater than (timestamp)"
                    },
                    "date_updated_lt": {
                        "type": "integer",
                        "description": "Date updated less than (timestamp)"
                    }
                }
            }
        ),
        Tool(
            name="get_task",
            description="Get a specific task by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID"
                    },
                    "custom_task_ids": {
                        "type": "boolean",
                        "description": "Use custom task IDs"
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (required for custom task IDs)"
                    },
                    "include_subtasks": {
                        "type": "boolean",
                        "description": "Include subtasks"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="create_task",
            description="Create a new task",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "The list ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Task name"
                    },
                    "description": {
                        "type": "string",
                        "description": "Task description"
                    },
                    "assignees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Assignee user IDs"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tag names"
                    },
                    "status": {
                        "type": "string",
                        "description": "Status name"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority (1=urgent, 2=high, 3=normal, 4=low)"
                    },
                    "due_date": {
                        "type": "integer",
                        "description": "Due date timestamp"
                    },
                    "due_date_time": {
                        "type": "boolean",
                        "description": "Include time in due date"
                    },
                    "start_date": {
                        "type": "integer",
                        "description": "Start date timestamp"
                    },
                    "start_date_time": {
                        "type": "boolean",
                        "description": "Include time in start date"
                    },
                    "notify_all": {
                        "type": "boolean",
                        "description": "Notify all assignees"
                    },
                    "parent": {
                        "type": "string",
                        "description": "Parent task ID"
                    },
                    "links_to": {
                        "type": "string",
                        "description": "Task ID to link to"
                    },
                    "check_required_custom_fields": {
                        "type": "boolean",
                        "description": "Check required custom fields"
                    },
                    "custom_fields": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Custom field values"
                    }
                },
                "required": ["list_id", "name"]
            }
        ),
        Tool(
            name="update_task",
            description="Update an existing task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "New task name"
                    },
                    "description": {
                        "type": "string",
                        "description": "New task description"
                    },
                    "status": {
                        "type": "string",
                        "description": "New status name"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority (1=urgent, 2=high, 3=normal, 4=low)"
                    },
                    "due_date": {
                        "type": "integer",
                        "description": "Due date timestamp"
                    },
                    "due_date_time": {
                        "type": "boolean",
                        "description": "Include time in due date"
                    },
                    "start_date": {
                        "type": "integer",
                        "description": "Start date timestamp"
                    },
                    "start_date_time": {
                        "type": "boolean",
                        "description": "Include time in start date"
                    },
                    "assignees": {
                        "type": "object",
                        "description": "Assignee configuration (add/rem arrays)"
                    },
                    "archived": {
                        "type": "boolean",
                        "description": "Archive status"
                    },
                    "parent": {
                        "type": "string",
                        "description": "Parent task ID"
                    },
                    "time_estimate": {
                        "type": "integer",
                        "description": "Time estimate in milliseconds"
                    },
                    "time_spent": {
                        "type": "integer",
                        "description": "Time spent in milliseconds"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="search_tasks",
            description="Search for tasks across workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team ID"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number"
                    }
                },
                "required": ["team_id"]
            }
        ),
        Tool(
            name="get_task_comments",
            description="Get comments for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="create_task_comment",
            description="Add a comment to a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID"
                    },
                    "comment_text": {
                        "type": "string",
                        "description": "Comment text"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Assignee user ID to notify"
                    },
                    "notify_all": {
                        "type": "boolean",
                        "description": "Notify all assignees"
                    }
                },
                "required": ["task_id", "comment_text"]
            }
        ),
        Tool(
            name="update_task_comment",
            description="Update a task comment",
            inputSchema={
                "type": "object",
                "properties": {
                    "comment_id": {
                        "type": "string",
                        "description": "The comment ID"
                    },
                    "comment_text": {
                        "type": "string",
                        "description": "New comment text"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Assignee user ID to notify"
                    }
                },
                "required": ["comment_id", "comment_text"]
            }
        ),
        Tool(
            name="get_task_dependencies",
            description="Get task dependencies",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="create_task_dependency",
            description="Create a task dependency",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID"
                    },
                    "depends_on": {
                        "type": "string",
                        "description": "Task ID this task depends on"
                    },
                    "dependency_of": {
                        "type": "string",
                        "description": "Task ID that depends on this task"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="get_task_time_entries",
            description="Get time entries for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="create_task_time_entry",
            description="Create a time entry for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID"
                    },
                    "start": {
                        "type": "integer",
                        "description": "Start time timestamp"
                    },
                    "billable": {
                        "type": "boolean",
                        "description": "Is billable"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Duration in milliseconds"
                    },
                    "description": {
                        "type": "string",
                        "description": "Time entry description"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Time entry tags"
                    }
                },
                "required": ["task_id", "start", "duration"]
            }
        ),
        Tool(
            name="get_task_attachments",
            description="Get attachments for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="get_task_watchers",
            description="Get watchers for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID"
                    }
                },
                "required": ["task_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Task Management category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_tasks":
        params = {}
        for key in ["archived", "page", "order_by", "reverse", "subtasks", "include_closed"]:
            if key in arguments:
                params[key] = arguments[key]
        if "statuses" in arguments:
            params["statuses[]"] = arguments["statuses"]
        if "assignees" in arguments:
            params["assignees[]"] = arguments["assignees"]
        if "tags" in arguments:
            params["tags[]"] = arguments["tags"]
        for key in ["due_date_gt", "due_date_lt", "date_created_gt", "date_created_lt", "date_updated_gt", "date_updated_lt"]:
            if key in arguments:
                params[key] = arguments[key]
        
        if "list_id" in arguments:
            response = await client.get(f"/list/{arguments['list_id']}/task", params=params)
        elif "folder_id" in arguments:
            response = await client.get(f"/folder/{arguments['folder_id']}/task", params=params)
        elif "space_id" in arguments:
            response = await client.get(f"/space/{arguments['space_id']}/task", params=params)
        else:
            return [TextContent(type="text", text='{"error": "list_id, folder_id, or space_id is required"}')]
        
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_task":
        task_id = arguments["task_id"]
        params = {}
        if "custom_task_ids" in arguments:
            params["custom_task_ids"] = arguments["custom_task_ids"]
        if "team_id" in arguments:
            params["team_id"] = arguments["team_id"]
        if "include_subtasks" in arguments:
            params["include_subtasks"] = arguments["include_subtasks"]
        response = await client.get(f"/task/{task_id}", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_task":
        list_id = arguments["list_id"]
        data = {"name": arguments["name"]}
        for key in ["description", "assignees", "tags", "status", "priority", "due_date", "due_date_time", 
                   "start_date", "start_date_time", "notify_all", "parent", "links_to", "check_required_custom_fields", "custom_fields"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.post(f"/list/{list_id}/task", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_task":
        task_id = arguments["task_id"]
        data = {}
        for key in ["name", "description", "status", "priority", "due_date", "due_date_time", 
                   "start_date", "start_date_time", "assignees", "archived", "parent", 
                   "time_estimate", "time_spent"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.put(f"/task/{task_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "search_tasks":
        team_id = arguments["team_id"]
        params = {"team_id": team_id}
        if "query" in arguments:
            params["query"] = arguments["query"]
        if "page" in arguments:
            params["page"] = arguments["page"]
        response = await client.get("/task", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_task_comments":
        task_id = arguments["task_id"]
        response = await client.get(f"/task/{task_id}/comment")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_task_comment":
        task_id = arguments["task_id"]
        data = {"comment_text": arguments["comment_text"]}
        if "assignee" in arguments:
            data["assignee"] = arguments["assignee"]
        if "notify_all" in arguments:
            data["notify_all"] = arguments["notify_all"]
        response = await client.post(f"/task/{task_id}/comment", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_task_comment":
        comment_id = arguments["comment_id"]
        data = {"comment_text": arguments["comment_text"]}
        if "assignee" in arguments:
            data["assignee"] = arguments["assignee"]
        response = await client.put(f"/comment/{comment_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_task_dependencies":
        task_id = arguments["task_id"]
        response = await client.get(f"/task/{task_id}/dependency")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_task_dependency":
        task_id = arguments["task_id"]
        data = {}
        if "depends_on" in arguments:
            data["depends_on"] = arguments["depends_on"]
        if "dependency_of" in arguments:
            data["dependency_of"] = arguments["dependency_of"]
        response = await client.post(f"/task/{task_id}/dependency", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_task_time_entries":
        task_id = arguments["task_id"]
        response = await client.get(f"/task/{task_id}/time")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_task_time_entry":
        task_id = arguments["task_id"]
        data = {
            "start": arguments["start"],
            "duration": arguments["duration"]
        }
        if "billable" in arguments:
            data["billable"] = arguments["billable"]
        if "description" in arguments:
            data["description"] = arguments["description"]
        if "tags" in arguments:
            data["tags"] = arguments["tags"]
        response = await client.post(f"/task/{task_id}/time", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_task_attachments":
        task_id = arguments["task_id"]
        response = await client.get(f"/task/{task_id}/attachment")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_task_watchers":
        task_id = arguments["task_id"]
        response = await client.get(f"/task/{task_id}/watcher")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
