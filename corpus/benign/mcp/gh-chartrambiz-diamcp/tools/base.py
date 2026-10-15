"""Tool decorator and base classes for dynamic MCP tools."""

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class ToolDefinition:
    name: str
    description: str
    func: Callable
    input_schema: dict


class ToolRegistry:
    _tools: dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, name: str, description: str, func: Callable, input_schema: dict):
        cls._tools[name] = ToolDefinition(
            name=name, description=description, func=func, input_schema=input_schema
        )

    @classmethod
    def get_all(cls) -> dict[str, ToolDefinition]:
        return cls._tools.copy()

    @classmethod
    def get(cls, name: str) -> Optional[ToolDefinition]:
        return cls._tools.get(name)

    @classmethod
    def clear(cls):
        cls._tools.clear()


def tool(name: str, description: str, schema: dict):
    """Decorator to register a function as an MCP tool.

    Usage:
        @tool(
            name="my_tool",
            description="Does something useful",
            schema={
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "The input"}
                },
                "required": ["input"]
            }
        )
        def my_tool(input: str) -> str:
            return f"Processed: {input}"
    """

    def decorator(func: Callable) -> Callable:
        ToolRegistry.register(name, description, func, schema)
        return func

    return decorator


def get_tools_from_module(module) -> list[ToolDefinition]:
    """Extract tool definitions from a module."""
    tools = []
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and ToolRegistry.get(name):
            tool_def = ToolRegistry.get(name)
            if tool_def and tool_def.func is obj:
                tools.append(tool_def)
    return tools
