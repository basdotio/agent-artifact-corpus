"""Custom Fields tools (6 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_custom_fields",
            description="Get custom fields for a list",
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
            name="get_custom_field",
            description="Get a specific custom field",
            inputSchema={
                "type": "object",
                "properties": {
                    "field_id": {
                        "type": "string",
                        "description": "Custom field ID"
                    }
                },
                "required": ["field_id"]
            }
        ),
        Tool(
            name="update_custom_field_value",
            description="Update a custom field value for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID"
                    },
                    "field_id": {
                        "type": "string",
                        "description": "Custom field ID"
                    },
                    "value": {
                        "description": "Field value (type depends on the custom field: text, number, date, dropdown option id, etc. - deliberately untyped in the schema)"
                    }
                },
                "required": ["task_id", "field_id", "value"]
            }
        ),
        Tool(
            name="create_custom_field",
            description="Create a custom field for a list",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "List ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Field name"
                    },
                    "type": {
                        "type": "string",
                        "description": "Field type (drop_down, text, number, date, checkbox, currency, email, phone, url, rating, label)"
                    },
                    "type_config": {
                        "type": "object",
                        "description": "Type-specific configuration (e.g., options for drop_down)"
                    }
                },
                "required": ["list_id", "name", "type"]
            }
        ),
        Tool(
            name="delete_custom_field",
            description="Delete a custom field",
            inputSchema={
                "type": "object",
                "properties": {
                    "field_id": {
                        "type": "string",
                        "description": "Custom field ID"
                    }
                },
                "required": ["field_id"]
            }
        ),
        Tool(
            name="remove_custom_field_value",
            description="Remove a custom field value from a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID"
                    },
                    "field_id": {
                        "type": "string",
                        "description": "Custom field ID"
                    }
                },
                "required": ["task_id", "field_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Custom Fields category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_custom_fields":
        list_id = arguments["list_id"]
        response = await client.get(f"/list/{list_id}/field")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_custom_field":
        field_id = arguments["field_id"]
        response = await client.get(f"/field/{field_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_custom_field_value":
        task_id = arguments["task_id"]
        field_id = arguments["field_id"]
        data = {"value": arguments["value"]}
        response = await client.post(f"/task/{task_id}/field/{field_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_custom_field":
        list_id = arguments["list_id"]
        data = {
            "name": arguments["name"],
            "type": arguments["type"]
        }
        if "type_config" in arguments:
            data["type_config"] = arguments["type_config"]
        response = await client.post(f"/list/{list_id}/field", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "delete_custom_field":
        field_id = arguments["field_id"]
        response = await client.delete(f"/field/{field_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Custom field deleted"}, indent=2))]

    elif name == "remove_custom_field_value":
        task_id = arguments["task_id"]
        field_id = arguments["field_id"]
        response = await client.delete(f"/task/{task_id}/field/{field_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Custom field value removed"}, indent=2))]

    return None
