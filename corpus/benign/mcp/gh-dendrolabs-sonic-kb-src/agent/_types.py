"""Agent type definitions -- tool calls, results, and definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}

    @classmethod
    def from_dict(cls, d: dict) -> ToolCall:
        return cls(id=d["id"], name=d["name"], arguments=d.get("arguments", {}))


@dataclass
class ToolResult:
    tool_call_id: str
    content: str
    is_error: bool = False

    def to_dict(self) -> dict:
        return {"tool_call_id": self.tool_call_id, "content": self.content, "is_error": self.is_error}

    @classmethod
    def from_dict(cls, d: dict) -> ToolResult:
        return cls(
            tool_call_id=d["tool_call_id"],
            content=d.get("content", ""),
            is_error=d.get("is_error", False),
        )


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict

    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}
