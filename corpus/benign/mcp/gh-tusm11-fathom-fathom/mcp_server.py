"""MCP server for Fathom diagnostic framework."""

import json
from fathom.api import FathomClient
from fathom.execution_adapter import MockTargetAgent


class FathomMCPServer:
    """MCP server wrapping FathomClient."""

    def __init__(self):
        self.client = FathomClient()
        self.active_profiles = {}  # system_id -> SystemProfile

    def get_tools(self) -> list[dict]:
        """Return tool definitions for MCP."""
        return [
            {
                "name": "create_profile",
                "description": "Create a new system profile for diagnostics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "system_id": {
                            "type": "string",
                            "description": "Unique identifier for the system being profiled",
                        }
                    },
                    "required": ["system_id"],
                },
            },
            {
                "name": "add_fact",
                "description": "Add a fact to a system profile (declared or observed)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "system_id": {
                            "type": "string",
                            "description": "System profile ID",
                        },
                        "category": {
                            "type": "string",
                            "description": "Fact category (e.g., 'tools', 'state')",
                        },
                        "key": {
                            "type": "string",
                            "description": "Fact key (e.g., 'has_web_access')",
                        },
                        "value": {
                            "type": "string",
                            "description": "Fact value (will auto-parse bool/int)",
                        },
                        "observed": {
                            "type": "boolean",
                            "description": "True for observed fact, False for declared",
                        },
                    },
                    "required": ["system_id", "category", "key", "value"],
                },
            },
            {
                "name": "diagnose",
                "description": "Run full diagnostic on a system profile",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "system_id": {
                            "type": "string",
                            "description": "System profile ID",
                        },
                        "executor_behavior": {
                            "type": "string",
                            "enum": ["consistent", "divergent"],
                            "description": "Mock executor behavior (consistent or divergent)",
                        },
                    },
                    "required": ["system_id"],
                },
            },
            {
                "name": "export_report",
                "description": "Export diagnostic report to JSON file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "system_id": {
                            "type": "string",
                            "description": "System profile ID",
                        },
                        "filepath": {
                            "type": "string",
                            "description": "Output filepath for JSON report",
                        },
                    },
                    "required": ["system_id", "filepath"],
                },
            },
            {
                "name": "get_skills",
                "description": "List all available diagnostic skills",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]
