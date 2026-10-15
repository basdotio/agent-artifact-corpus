"""Base class cho tất cả MCP tools."""

from abc import ABC, abstractmethod
from typing import Any

from mcp.types import TextContent, Tool
from pydantic import BaseModel


class BaseTool(ABC):
    """Base class cho tất cả MCP tools."""

    # ============================================================
    # PROPERTIES (bắt buộc implement)
    # ============================================================
    @property
    @abstractmethod
    def name(self) -> str:
        """Tên tool — unique, snake_case."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Mô tả tool — LLM đọc để biết khi nào dùng."""
        ...

    @property
    @abstractmethod
    def input_model(self) -> type[BaseModel]:
        """Pydantic model để validate input."""
        ...

    # ============================================================
    # PROPERTIES (có default)
    # ============================================================
    @property
    def annotations(self) -> dict[str, Any]:
        """MCP annotations — hints về behavior."""
        return {
            "title": self.name.replace("_", " ").title(),
            "readOnlyHint": True,
            "idempotentHint": True,
            "destructiveHint": False,
            "openWorldHint": False,
        }

    # ============================================================
    # METHODS
    # ============================================================
    def to_mcp_tool(self) -> Tool:
        """Convert sang MCP Tool format.

        Note: MCP SDK 2.x dùng snake_case (input_schema), không phải camelCase.
        """
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_model.model_json_schema(),
            annotations=self.annotations,
        )

    @abstractmethod
    async def execute(
        self,
        arguments: dict[str, Any],
        context: Any,
    ) -> list[TextContent]:
        """Thực thi tool."""
        ...

    # ============================================================
    # HELPERS
    # ============================================================
    def error_response(self, message: str) -> list[TextContent]:
        """Tạo response lỗi chuẩn."""
        return [TextContent(type="text", text=f"Error: {message}")]

    def success_response(self, message: str) -> list[TextContent]:
        """Tạo response thành công chuẩn."""
        return [TextContent(type="text", text=message)]
